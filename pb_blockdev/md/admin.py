#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: All modules for handling mdadm actions independent
          of a particular MD device
"""

# Standard modules
import sys
import os
import re
import logging
import socket
import uuid
import signal
import errno
import datetime

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust
from pb_base.common import to_str_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_base.errors import CouldntOccupyLockfileError
from pb_base.handler.lock import PbLock
from pb_base.handler.lock import PbLockHandler
from pb_base.handler.lock import LockHandlerError

from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDevice
from pb_blockdev.base import BASE_SYSFS_BLOCKDEV_DIR

from pb_blockdev.md import is_md_uuid, uuid_to_md, uuid_from_md
from pb_blockdev.md import GenericMdError, MdadmError, MdadmTimeoutError
from pb_blockdev.md import DEFAULT_MDADM_LOCKFILE, MD_UUID_TOKEN
from pb_blockdev.md import DEFAULT_MDADM_TIMEOUT
from pb_blockdev.md import GenericMdHandler

from pb_blockdev.translate import translator, pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.4.3'

LOG = logging.getLogger(__name__)

DEFAULT_MD_FORMAT = '1.2'
DEFAULT_HOMEHOST = 'virtualhost'
DEFAULT_ARRAY_NAME = '0'

MD_DATE_FORMAT = '%a %b %d %H:%M:%S %Y'

VALID_MD_FORMATS = ('0', '0.90', '1', '1.0', '1.1', '1.2', 'default')
"""
A list of all available RAID metadata (superblock) formats,
that can be used.
"""

VALID_MD_LEVELS = (
        'linear', 'raid0', '0', 'stripe',
        'raid1', '1', 'mirror',
        'raid4', '4',
        'raid5', '5',
        'raid6', '6',
        'raid10', '10',
)
"""
A list of all available RAID levels, that canbe used to create a new MD device.
Following md levels are possible for mdadm, but not supported in this module::
 * multipath
 * mp
 * faulty
 * container
"""


# =============================================================================
def parse_date(date_string):
    """
    Tries to parse the given date string as a date formatted in US locale
    format.

    @raise ValueError: if the date_string could not be parsed.

    @param date_string: the date string to parse
    @type date_string: str

    @return: the parsed date as a datetime object with time zone UTC
    @rtype: datetime.datetime

    """

    return datetime.datetime.strptime(date_string, MD_DATE_FORMAT)

# =============================================================================
class MdadmDumpError(MdadmError, IOError):
    """Special exception class for timeout on dumping a device."""

    # -------------------------------------------------------------------------
    def __init__(self, timeout, device):
        """
        Constructor.

        @param timeout: the timout in seconds leading to the error
        @type timeout: float
        @param device: the device, which which should be dumped
        @type device: str

        """

        t_o = None
        try:
            t_o = float(timeout)
        except ValueError:
            pass
        self.timeout = t_o

        strerror = _("Timeout on dumping")

        if t_o is not None:
            strerror += _(" (timeout after %0.1f secs)") % (t_o)

        super(MdadmDumpError, self).__init__(errno.ETIMEDOUT, strerror, device)


# =============================================================================
class MdSuperblock(PbBaseObject):
    """
    Encapsulation class for MD superblock informations
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None,
        use_stderr=False, initialized=False, *targs, **kwargs
        ):
        """
        Initialisation of the MdSuperblock object

        @raise MdadmError: on a uncoverable error.

        @param appname: name of the current running application
        @type appname: str
        @param verbose: verbose level
        @type verbose: int
        @param version: the version string of the current object or application
        @type version: str
        @param base_dir: the base directory of all operations
        @type base_dir: str
        @param use_stderr: a flag indicating, that on handle_error() the output
                           should go to STDERR, even if logging has
                           initialized logging handlers.
        @type use_stderr: bool

        @return: None

        """

        self._magic = None
        self._sb_version = None
        self._array_uuid = None
        self._name = None
        self._creation_time = None
        self._update_time = None
        self._raid_level = None
        self._raid_devices = None
        self._state = None
        self._device_uuid = None
        self._flags = None
        self._bitmap = None
        self._chunk_size = None

        self._raw_info = None

        super(MdSuperblock, self).__init__(
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            initialized=False,
        )

        self._init_properties(**kwargs)

        if initialized:
            self.initialized = True

    # -----------------------------------------------------------
    @property
    def magic(self):
        """The magic number of the superblock."""
        return self._magic

    @magic.setter
    def magic(self, value):
        if value is None:
            self._magic = None
            return
        if isinstance(value, int):
            self._magic = value
            return
        if sys.version_info[0] <= 2:
            if isinstance(value, long):
                self._magic = int(value)
                return
        v = str(value)
        self._magic = int(v, 16)
        return

    # -----------------------------------------------------------
    @property
    def sb_version(self):
        """The format version of the superblock."""
        return self._sb_version

    @sb_version.setter
    def sb_version(self, value):
        if value is None:
            self._sb_version = None
            return
        self._sb_version = str(value)

    # -----------------------------------------------------------
    @property
    def array_uuid(self):
        """The UUID of the appropriate MD Raid."""
        return self._array_uuid

    @array_uuid.setter
    def array_uuid(self, value):
        if value is None:
            self._array_uuid = None
            return
        if isinstance(value, uuid.UUID):
            self._array_uuid = value
            return
        if is_md_uuid(value):
            self._array_uuid = uuid_from_md(value)
            return
        self._array_uuid = uuid.UUID(value)

    # -----------------------------------------------------------
    @property
    def device_uuid(self):
        """The device UUID of the superblock."""
        return self._device_uuid

    @device_uuid.setter
    def device_uuid(self, value):
        if value is None:
            self._device_uuid = None
            return
        if isinstance(value, uuid.UUID):
            self._device_uuid = value
            return
        if is_md_uuid(value):
            self._device_uuid = uuid_from_md(value)
            return
        self._device_uuid = uuid.UUID(value)

    # -----------------------------------------------------------
    @property
    def name(self):
        """The name of the appropriate MD Raid."""
        return self._name

    @name.setter
    def name(self, value):
        if value is None:
            self._name = None
            return
        self._name = str(value)

    # -----------------------------------------------------------
    @property
    def creation_time(self):
        """The timestamp of creation the RAID device."""
        return self._creation_time

    @creation_time.setter
    def creation_time(self, value):
        if value is None:
            self._creation_time = None
            return
        if isinstance(value, datetime.datetime):
            self._creation_time = value
            return
        self._creation_time = parse_date(str(value))

    # -----------------------------------------------------------
    @property
    def update_time(self):
        """The timestamp of last update of the MD superblock."""
        return self._update_time

    @update_time.setter
    def update_time(self, value):
        if value is None:
            self._update_time = None
            return
        if isinstance(value, datetime.datetime):
            self._update_time = value
            return
        self._update_time = parse_date(str(value))

    # -----------------------------------------------------------
    @property
    def raid_level(self):
        """The RAID level of the MD RAID device."""
        return self._raid_level

    @raid_level.setter
    def raid_level(self, value):
        if value is None:
            self._raid_level = None
            return
        self._raid_level = str(value)

    # -----------------------------------------------------------
    @property
    def raid_devices(self):
        """The total number of devices of the MD RAID device."""
        return self._raid_devices

    @raid_devices.setter
    def raid_devices(self, value):
        if value is None:
            self._raid_devices = None
            return
        self._raid_devices = int(value)

    # -----------------------------------------------------------
    @property
    def state(self):
        """The state of the MD superblock."""
        return self._state

    @state.setter
    def state(self, value):
        if value is None:
            self._state = None
            return
        self._state = str(value)

    # -----------------------------------------------------------
    @property
    def bitmap(self):
        """Informations about the internal bitmap of the MD superblock."""
        return self._bitmap

    @bitmap.setter
    def bitmap(self, value):
        if value is None:
            self._bitmap = None
            return
        self._bitmap = str(value)

    # -----------------------------------------------------------
    @property
    def raw_info(self):
        """The raw information about the suberblock
           how given by 'mdadm --examine'."""
        return self._raw_info

    # -------------------------------------------------------------------------
    def _init_properties(self, **kwargs):
        """Initialisation of all special MS superblock properties."""

        if 'magic' in kwargs:
            self.magic = kwargs['magic']
        if 'sb_version' in kwargs:
            self.sb_version = kwargs['sb_version']
        if 'array_uuid' in kwargs:
            self.array_uuid = kwargs['array_uuid']
        if 'name' in kwargs:
            self.name = kwargs['name']
        if 'creation_time' in kwargs:
            self.creation_time = kwargs['creation_time']
        if 'update_time' in kwargs:
            self.update_time = kwargs['update_time']
        if 'raid_level' in kwargs:
            self.raid_level = kwargs['raid_level']
        if 'raid_devices' in kwargs:
            self.raid_devices = kwargs['raid_devices']
        if 'state' in kwargs:
            self.state = kwargs['state']
        if 'bitmap' in kwargs:
            self.bitmap = kwargs['bitmap']
        if 'device_uuid' in kwargs:
            self.device_uuid = kwargs['device_uuid']

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MdSuperblock, self).as_dict(short=short)
        res['magic'] = None
        if self.magic is not None:
            res['magic'] = "0x%08x" % (self.magic)
        res['sb_version'] = self.sb_version
        res['array_uuid'] = self.array_uuid
        res['name'] = self.name
        res['creation_time'] = self.creation_time
        res['update_time'] = self.update_time
        res['raid_level'] = self.raid_level
        res['raid_devices'] = self.raid_devices
        res['state'] = self.state
        res['bitmap'] = self.bitmap
        res['device_uuid'] = self.device_uuid

        res['raw_info'] = self.raw_info

        return res

    # -------------------------------------------------------------------------
    @classmethod
    def from_examine(
        cls, examine_out, appname=None, verbose=0, version=__version__,
            base_dir=None, use_stderr=False, initialized=False):
        """
        Creating a MdSuperblock from output of 'mdadm --examine'.

        @raise MdadmError: on a uncoverable error.

        @param appname: name of the current running application
        @type appname: str
        @param verbose: verbose level
        @type verbose: int
        @param version: the version string of the current object or application
        @type version: str
        @param base_dir: the base directory of all operations
        @type base_dir: str
        @param use_stderr: a flag indicating, that on handle_error() the output
                           should go to STDERR, even if logging has
                           initialized logging handlers.
        @type use_stderr: bool

        @return: None

        """

        sb = cls(
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            initialized=False,
        )

        eout = examine_out.strip()
        sb._raw_info = eout

        re_magic = re.compile(r'^Magic\s*:\s*(?:0x)?([0-9a-f]+)', re.IGNORECASE)
        re_version = re.compile(r'^Version\s*:\s*(\S+)', re.IGNORECASE)
        pattern_array_uuid = r'^(?:Array\s+)*UUID\s*:\s*'
        pattern_array_uuid += r'(' + MD_UUID_TOKEN + r':' + MD_UUID_TOKEN + r':'
        pattern_array_uuid += MD_UUID_TOKEN + r':' + MD_UUID_TOKEN + r')'
        if verbose > 2:
            LOG.debug((_(
                "Regex to analyze output of %(w)r:") + ' %(r)r') % {
                'w': 'mdadm --examine', 'r': pattern_array_uuid})
        re_array_uuid = re.compile(pattern_array_uuid, re.IGNORECASE)
        pattern_device_uuid = r'^(?:Device\s+)*UUID\s*:\s*'
        pattern_device_uuid += r'(' + MD_UUID_TOKEN + r':' + MD_UUID_TOKEN + r':'
        pattern_device_uuid += MD_UUID_TOKEN + r':' + MD_UUID_TOKEN + r')'
        re_device_uuid = re.compile(pattern_device_uuid, re.IGNORECASE)
        re_name = re.compile(r'^Name\s*:\s*(.*)(?:\s+\(local\s+to\s+host.*\))?',
                re.IGNORECASE)
        re_creation_time = re.compile(r'^Creation\s+Time\s*:\s*(.*)',
                re.IGNORECASE)
        re_update_time = re.compile(r'^Update\s+Time\s*:\s*(.*)',
                re.IGNORECASE)
        re_raid_level = re.compile(r'^Raid\s+Level\s*:\s*(\S+)', re.IGNORECASE)
        re_raid_devices = re.compile(r'^Raid\s+Devices\s*:\s*(\d+)', re.IGNORECASE)
        re_state = re.compile(r'^State\s*:\s*(.+)', re.IGNORECASE)
        re_bitmap = re.compile(r'^Internal\s+Bitmap\s*:\s*(.+)', re.IGNORECASE)

        for line in eout.splitlines():

            l = line.strip()
            if l == '':
                continue

            match = re_magic.search(l)
            if match:
                sb.magic = match.group(1)
                continue

            match = re_version.search(l)
            if match:
                sb.sb_version = match.group(1)
                continue

            match = re_array_uuid.search(l)
            if match:
                sb.array_uuid = match.group(1)
                continue

            match = re_name.search(l)
            if match:
                sb.name = match.group(1)
                continue

            match = re_creation_time.search(l)
            if match:
                sb.creation_time = match.group(1)
                continue

            match = re_update_time.search(l)
            if match:
                sb.update_time = match.group(1)
                continue

            match = re_raid_level.search(l)
            if match:
                sb.raid_level = match.group(1)
                continue

            match = re_raid_devices.search(l)
            if match:
                sb.raid_devices = match.group(1)
                continue

            match = re_state.search(l)
            if match:
                sb.state = match.group(1)
                continue

            match = re_bitmap.search(l)
            if match:
                sb.bitmap = match.group(1)
                continue

            match = re_device_uuid.search(l)
            if match:
                sb.device_uuid = match.group(1)
                continue

        if initialized:
            sb.initialized = True
        return sb

# =============================================================================
class MdAdm(GenericMdHandler):
    """
    Class for a MdAdm handler Object for all actions around mdadm
    independent of a particular MD device
    """

    # -------------------------------------------------------------------------
    def __init__(
        self,
            default_md_format=DEFAULT_MD_FORMAT,
            default_homehost=DEFAULT_HOMEHOST,
            default_array_name=DEFAULT_ARRAY_NAME,
            mdadm_command=None, mdadm_lockfile=DEFAULT_MDADM_LOCKFILE,
            mdadm_timeout=DEFAULT_MDADM_TIMEOUT,
            appname=None, verbose=0, version=__version__, base_dir=None,
            use_stderr=False, initialized=False, simulate=False, sudo=False,
            quiet=False, *targs, **kwargs
            ):
        """
        Initialisation of the mdadm handler object.

        @raise CommandNotFoundError: if the command 'mdadm'
                                     could not be found
        @raise MdadmError: on a uncoverable error.

        @param default_md_format: default format of the metadata superblock,
                                  that is used for creating the new
                                  metadevice, if None is given
        @type default_md_format: str
        @param default_homehost: homehost option used for creating a special
                                 degraded RAID device
        @type default_homehost: str
        @param default_array_name: default name of the array on some circumstances
                                   (if needed)
        @type default_array_name: str
        @param mdadm_command: path to executable mdadm command
        @type mdadm_command: str
        @param mdadm_lockfile: the global lockfile used for mdadm execution
        @type mdadm_lockfile: str
        @param mdadm_timeout: timeout for execution the mdadm command
        @type mdadm_timeout: int or None

        @param appname: name of the current running application
        @type appname: str
        @param verbose: verbose level
        @type verbose: int
        @param version: the version string of the current object or application
        @type version: str
        @param base_dir: the base directory of all operations
        @type base_dir: str
        @param use_stderr: a flag indicating, that on handle_error() the output
                           should go to STDERR, even if logging has
                           initialized logging handlers.
        @type use_stderr: bool
        @param simulate: don't execute actions, only display them
        @type simulate: bool
        @param sudo: should the command executed by sudo by default
        @type sudo: bool
        @param quiet: don't display ouput of action after calling
        @type quiet: bool

        @return: None

        """

        self._default_md_format = default_md_format
        """
        @ivar: format of the metadata superblock, that is used for
               creating the new metadevice, if None is given
        @type: str
        """

        self._default_homehost = default_homehost
        """
        @ivar: homehost option used for creating our special degraded RAID device
        @type: str
        """

        self._default_array_name = default_array_name
        """
        @ivar: default name of the array on some circumstances (if needed)
        @type: str
        """

        # Initialisation of the parent object
        super(MdAdm, self).__init__(
            mdadm_command=mdadm_command,
            mdadm_lockfile=mdadm_lockfile,
            mdadm_timeout=mdadm_timeout,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            initialized=False,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )

        if not self.default_md_format:
            self._default_md_format = DEFAULT_MD_FORMAT
        if not self.default_homehost:
            self._default_homehost = DEFAULT_HOMEHOST
        if not self.default_array_name:
            self._default_array_name = DEFAULT_ARRAY_NAME

        self.initialized = True

    # -----------------------------------------------------------
    @property
    def default_md_format(self):
        """The format of the metadata superblock, that is used for creating."""
        return self._default_md_format

    # -----------------------------------------------------------
    @property
    def default_homehost(self):
        """The homehost option used for creating our special degraded RAID device."""
        return self._default_homehost

    # -----------------------------------------------------------
    @property
    def default_array_name(self):
        """The default name of the array on some circumstances (if needed)."""
        return self._default_array_name

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MdAdm, self).as_dict(short=short)
        res['default_md_format'] = self.default_md_format
        res['default_homehost'] = self.default_homehost
        res['default_array_name'] = self.default_array_name

        return res

    # -------------------------------------------------------------------------
    def _get_new_md_device_id(self, release_lock=False):
        """
        Retrieve a new, unused MD device id. It sets first a lock for this
        action.

        @raise MdadmError: if the lock could not be created.

        @param release_lock: release the global lock after finding
                             the new device Id
        @type release_lock: bool

        @return: the new md device id
        @rtype: int

        """

        md_id = None

        if not self.global_lock:
            self.lock_global()

        i = 0
        max_id = 10000
        while md_id is None:
            dev_dir = os.path.join(BASE_SYSFS_BLOCKDEV_DIR, ('md%d' % (i)))
            if not os.path.exists(dev_name):
                md_id = i
                break
            i += 1
            if i >= max_id:
                msg = _("Maximum MD ID of %d reached.") % (max_id)
                self.global_lock = None
                raise MdadmError(msg)

        if release_lock:
            self.global_lock = None

        return md_id

    # -------------------------------------------------------------------------
    def zero_superblock(self, device, timeout=300, no_dump=False, sudo=None):
        """
        Ensures the removing/overwriting a possibly existing superblock
        on the given device. Additionally the first 4 MiBytes of this device
        will be overwritten with binary Null.

        @param device: the device file name, where to zeroing the superblock.
                       It must exist in the filesystem before.
        @type device: BlockDevice
        @param timeout: the timeout on writing on the device.
        @type timeout: int
        @param no_dump: don't execute overwriting of the first 4 MiByte of the
                      device, only execute 'mdadm --zero-superblock'
        @type no_dump: bool
        @param sudo: execute mdadm with sudo as root
        @type sudo: bool or None

        @raise ValueError: if parameter device is not a BlockDevice
        @raise PbBaseHandlerError: on errors on dumping
        @raise MdadmDumpError: on timeout on dumping the BlockDevice
        @raise MdadmError: on different errors.

        @return: None

        """

        if not isinstance(device, BlockDevice):
            msg = _(
                "Parameter %(p)r must be of type %(t)r, but is of type %(i)r instead.") % {
                'p': 'device', 't': 'BlockDevice', 'i': device.__class__.__name__}
            raise ValueError(msg)

        if not device.exists:
            msg = _("Device %r does not exist.") % (device.name)
            raise MdadmError(msg)

        def dump_alarm_caller(signum, sigframe):
            '''
            This nested function will be called in event of a timeout

            @param signum:   the signal number (POSIX) which happend
            @type signum:    int
            @param sigframe: the frame of the signal
            @type sigframe:  object
            '''

            raise MdadmDumpError(timeout, device.name)

        # Execute 'mdadm --zero-superblock --force'
        LOG.info(_("Zeroing MD superblock on device %r."), device.device)
        args = ['--zero-superblock', '--force', device.device]
        (ret_code, std_out, std_err) = self.exec_mdadm(
            'manage', args, sudo=sudo)

        # Now write over the first 4 MiBytes on this device
        if not no_dump:
            LOG.debug(__(
                "Dumping %(d)r, timeout %(t)d second.",
                "Dumping %(d)r, timeout %(t)d seconds.",
                timeout) % {
                    'd': device.device,
                    't': timeout})
            bs = 1024 * 1024
            signal.signal(signal.SIGALRM, dump_alarm_caller)
            signal.alarm(timeout)
            try:
                device.wipe(blocksize=bs, count=4)
            finally:
                signal.alarm(0)

        return

    # -------------------------------------------------------------------------
    def examine(self, path, sudo=None):
        """
        Examines the given path for a MD superblock. The path must be either
        an existing block device or an existing filename.

        @raise ValueError: if the given path is unusable
        @raise MdadmTimeoutError: on timeout on examining the path
        @raise MdadmError: on a uncoverable error.

        @param path: the existing block device or plain file to examine
                     for the MD superblock
        @type path: BlockDevice or str
        @param sudo: execute mdadm with sudo as root
        @type sudo: bool or None

        @return: the superblock information or None, if nothing was found
        @rtype: MdSuperblock or None

        """

        dev = None
        msg = _("Cannot examine %r, because it does not exists.")
        if isinstance(path, BlockDevice):
            dev = path.device
            if not path.exists:
                raise ValueError(msg % (dev))
        else:
            dev = path
            if not os.path.exists(dev):
                raise ValueError(msg % (dev))

        LOG.debug(_("Examining MD superblock on %r ..."), dev)
        args = ['--examine', dev]
        (ret_code, std_out, std_err) = self.exec_mdadm(
            'manage', args, sudo=sudo, force=True)

        if ret_code:
            LOG.debug(_("No MD superblock on %(d)r found: %(m)s") % {
                'd': dev, 'm': std_err})
            return None

        sb = MdSuperblock.from_examine(
            std_out,
            appname=self.appname,
            verbose=self.verbose,
            base_dir=self.base_dir,
            initialized=True,
        )

        return sb


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
