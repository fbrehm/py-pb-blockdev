#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Encapsulation module for a MD Raid device
"""

# Standard modules
import sys
import os
import re
import logging
import time

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust
from pb_base.common import to_str_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

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

__version__ = '0.2.5'

LOG = logging.getLogger(__name__)
RE_MD_ID = re.compile(r'^md(\d+)$')


# =============================================================================
class MdDeviceError(GenericMdError, BlockDeviceError):
    """Base exception class for all errors with MD devices."""
    pass


# =============================================================================
class MdDevice(BlockDevice, GenericMdHandler):
    """Encapsulation class for a multipath device."""

    # -------------------------------------------------------------------------
    def __init__(
        self, name=None, auto_discover=False,
            mdadm_command=None, mdadm_lockfile=DEFAULT_MDADM_LOCKFILE,
            mdadm_timeout=DEFAULT_MDADM_TIMEOUT, appname=None, verbose=0,
            version=__version__, base_dir=None, use_stderr=False,
            simulate=False, sudo=False, quiet=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the MdDevice object.

        @raise CommandNotFoundError: if the command 'mdadm'
                                     could not be found
        @raise ValueError: On a wrong mdadm_timeout or a wrong name
        @raise MdDeviceError: on a uncoverable error.

        @param name: name of the MD Raid device, e.g. 'md1'
        @type name: str
        @param auto_discover: discover paths and properties automatacally
                              after init of this object.
        @type auto_discover: bool

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

        self._discovered = False

        self._md_id = None
        """
        @ivar: The numeric Id of the MD device
        @type: int
        """
        if name is not None:
            match = RE_MD_ID.search(name)
            if not match:
                msg = _("Invalid name %r of a MD device given.")
                raise ValueError(msg % (name))
            self._md_id = int(match.group(1))

        self.sub_devs = []
        """
        @ivar: list of all child devices of this MD device
        @type: list of MdSubdevice
        """

        self._level = None
        """
        @ivar: the RAID level of this RAID device
        @type: str
        """

        self._md_version = None
        """
        @ivar: the version of the format of the superblock.
        @type: str
        """

        self._chunk_size = None
        """
        @ivar: the chunk size of the array in Bytes,
               for raid levels 0, 4, 5, 6 and 10,
               else allways 0
        @type: int
        """

        self._raid_disks = None
        """
        @ivar: the number of used raid devices
        @type: int
        """

        self._total_devices = None
        """
        @ivar: the number of all used devices (including spare)
        @type: int
        """

        self._state = None
        """
        @ivar: the state of the array, possible values:
                * clear
                * inactive
                * suspended (not supported yet)
                * readonly
                * read-auto
                * clean
                * active
                * write-pending
                * active-idle
        @type: str
        """

        self._degraded = None
        """
        @ivar: is the array currently in a degraded state?
        @type: bool
        """

        self._sync_action = None
        """
        @ivar: the current sync action of an array with redundancy (raid
               levels 1, 4, 5, 6). Possible values are::

                * resync
                * recover
                * idle
                * check
                * repair

        @type: str
        """

        self._uuid = None
        """
        @ivar: the UUID of this array
        @type: uuid.UUID
        """

        # Initialisation of the parent object
        super(MdDevice, self).__init__(
            name=name,
            mdadm_command=mdadm_command,
            mdadm_lockfile=mdadm_lockfile,
            mdadm_timeout=mdadm_timeout,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
            initialized=False,
            *targs, **kwargs
        )

        if auto_discover:
            self.discover()

        self.initialized = True
        if self.verbose > 3:
            LOG.debug(_("Initialized."))

    # -----------------------------------------------------------
    @property
    def md_id(self):
        """The numeric Id of the MD device."""
        return self._md_id

    # -----------------------------------------------------------
    @property
    def sysfs_md_dir(self):
        """The directory in sysfs for the MD device, e.g. /sys/block/md0/md"""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'md')

    # -----------------------------------------------------------
    @property
    def sysfs_md_dir_real(self):
        """The real path of the MD device dir in sysfs."""
        if not self.sysfs_md_dir:
            return None
        if not os.path.exists(self.sysfs_md_dir):
            return None
        return os.path.realpath(self.sysfs_md_dir)

    # -----------------------------------------------------------
    @property
    def level_file(self):
        """The file in sysfs containing the raid level."""
        if not self.sysfs_md_dir:
            return None
        return os.path.join(self.sysfs_md_dir, 'level')

    # -----------------------------------------------------------
    @property
    def md_version_file(self):
        """The file in sysfs containing the metadata version."""
        if not self.sysfs_md_dir:
            return None
        return os.path.join(self.sysfs_md_dir, 'metadata_version')

    # -----------------------------------------------------------
    @property
    def md_version(self):
        """The version of the metadata of this RAID device."""
        if self._md_version is not None:
            return self._md_version
        if not self.exists:
            return None
        self.retr_md_version()
        return self._md_version

    # -----------------------------------------------------------
    @property
    def chunk_size_file(self):
        """The file in sysfs containing the chunk size of the MD Raid."""
        if not self.sysfs_md_dir:
            return None
        return os.path.join(self.sysfs_md_dir, 'chunk_size')

    # -----------------------------------------------------------
    @property
    def chunk_size(self):
        """The chunk size of the MD Raid device."""
        if self._chunk_size is not None:
            return self._chunk_size
        if not self.exists:
            return None
        self.retr_chunk_size()
        return self._chunk_size

    # -----------------------------------------------------------
    @property
    def state_file(self):
        """The file in sysfs containing the state of the MD Raid."""
        if not self.sysfs_md_dir:
            return None
        return os.path.join(self.sysfs_md_dir, 'array_state')

    # -----------------------------------------------------------
    @property
    def state(self):
        """The state of the MD Raid device."""
        if self._state is not None:
            return self._state
        if not self.exists:
            return None
        self.retr_state()
        return self._state

    # -----------------------------------------------------------
    @property
    def degraded_file(self):
        """The file in sysfs containing the degraded state of the MD Raid."""
        if not self.sysfs_md_dir:
            return None
        return os.path.join(self.sysfs_md_dir, 'degraded')

    # -----------------------------------------------------------
    @property
    def degraded(self):
        """The degraded state of the MD Raid device."""
        if self._degraded is not None:
            return self._degraded
        if not self.exists:
            return None
        self.retr_degraded()
        return self._degraded

    # -----------------------------------------------------------
    @property
    def raid_disks_file(self):
        """The file in sysfs containing the number of raid disks of the MD Raid."""
        if not self.sysfs_md_dir:
            return None
        return os.path.join(self.sysfs_md_dir, 'raid_disks')

    # -----------------------------------------------------------
    @property
    def raid_disks(self):
        """The number of raid disks of the MD Raid device."""
        if self._raid_disks is not None:
            return self._raid_disks
        if not self.exists:
            return None
        self.retr_raid_disks()
        return self._raid_disks

    # -----------------------------------------------------------
    @property
    def discovered(self):
        """Was the MD device already discovered."""
        return self._discovered

    # -----------------------------------------------------------
    @property
    def level(self):
        """The RAID level of this RAID device."""
        if self._level is not None:
            return self._level
        if not self.exists:
            return None
        self.retr_level()
        return self._level

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MdDevice, self).as_dict(short=short)
        res['discovered'] = self.discovered
        res['md_id'] = self.md_id
        res['sysfs_md_dir'] = self.sysfs_md_dir
        res['sysfs_md_dir_real'] = self.sysfs_md_dir_real
        res['level_file'] = self.level_file
        res['level'] = self.level
        res['md_version_file'] = self.md_version_file
        res['md_version'] = self.md_version
        res['chunk_size_file'] = self.chunk_size_file
        res['chunk_size'] = self.chunk_size
        res['degraded_file'] = self.degraded_file
        res['degraded'] = self.degraded
        res['state_file'] = self.state_file
        res['state'] = self.state
        res['raid_disks_file'] = self.raid_disks_file
        res['raid_disks'] = self.raid_disks

        res['sub_devs'] = []
        for subdev in self.sub_devs:
            res['sub_devs'].append(subdev.as_dict(short=short))

        return res

    # -------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable MD Raid device.

        @raise MdDeviceError: if the given device name is invalid,

        @param device_name: the basename of the MD device to check, e.g. 'md1'
        @type device_name: str

        @return: the given device name is usable as a MD device name and exists.
        @rtype: bool

        """

        if not device_name:
            raise MdDeviceError(_("No device name given."))
        if device_name != os.path.basename(device_name):
            msg = _("Invalid device name %r given.") % (device_name)
            raise MdDeviceError(msg)

        bd_dir = os.sep + os.path.join('sys', 'block', device_name)
        if not os.path.exists(bd_dir):
            return False

        md_dir = os.path.join(bd_dir, 'md')
        if not os.path.exists(md_dir):
            return False
        if not os.path.isdir(md_dir):
            return False

        return True

    # -------------------------------------------------------------------------
    def discover(self):
        """
        Discovering of all properties and paths of this multipath device.
        """

        self._discovered = False
        self.sub_devs = []
        self._level = None
        self._md_version = None
        self._chunk_size = None
        self._raid_disks = None
        self._total_devices = None
        self._state = None
        self._degraded = None
        self._sync_action = None
        self._uuid = None

        if not self.exists:
            return

        self.retr_level()
        self.retr_md_version()
        self.retr_chunk_size()
        self.retr_state()
        self.retr_raid_disks()

        self._discovered = True

    # -------------------------------------------------------------------------
    def retr_level(self):
        """
        A method to retrieve the raid level from sysfs

        @raise MdDeviceError: if the level file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve RAID level, because it's an unnamed MD device object.")
            raise MdDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve RAID level of %r, because the MD device doesn't exists.") % (self.name)
            raise MdDeviceError(msg)

        l_file = self.level_file
        if not os.path.exists(l_file):
            msg = _(
                "Cannot retrieve RAID level of %(bd)r, because the file %(file)r doesn't exists.") % {
                'bd': self.name, 'file': l_file}
            raise MdDeviceError(msg)

        if not os.access(l_file, os.R_OK):
            msg = _(
                "Cannot retrieve RAID level of %(bd)r, because no read access to %(file)r.") % {
                'bd': self.name, 'file': l_file}
            raise MdDeviceError(msg)

        f_content = self.read_file(l_file, quiet=True).strip()
        if not f_content:
            msg = _(
                "Cannot retrieve RAID level state of %(bd)r, because file %(file)r has no content.") % {
                'bd': self.name, 'file': l_file}
            raise MdDeviceError(msg)

        self._level = f_content

    # -------------------------------------------------------------------------
    def retr_md_version(self):
        """
        A method to retrieve the version of the metadata from sysfs

        @raise MdDeviceError: if the md_version file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve metadata version, because it's an unnamed MD device object.")
            raise MdDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve metadata version of %r, because the MD device doesn't exists.") % (self.name)
            raise MdDeviceError(msg)

        v_file = self.md_version_file
        if not os.path.exists(v_file):
            msg = _(
                "Cannot retrieve metadata version of %(bd)r, because the file %(file)r doesn't exists.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        if not os.access(v_file, os.R_OK):
            msg = _(
                "Cannot retrieve metadata version of %(bd)r, because no read access to %(file)r.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        f_content = self.read_file(v_file, quiet=True).strip()
        if not f_content:
            msg = _(
                "Cannot retrieve metadata version state of %(bd)r, because file %(file)r has no content.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        self._md_version = f_content

    # -------------------------------------------------------------------------
    def retr_chunk_size(self):
        """
        A method to retrieve the chunk size of the MD Raid device from sysfs

        @raise MdDeviceError: if the chunk_size file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve chunk size, because it's an unnamed MD device object.")
            raise MdDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve chunk size of %r, because the MD device doesn't exists.") % (self.name)
            raise MdDeviceError(msg)

        v_file = self.chunk_size_file
        if not os.path.exists(v_file):
            msg = _(
                "Cannot retrieve chunk size of %(bd)r, because the file %(file)r doesn't exists.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        if not os.access(v_file, os.R_OK):
            msg = _(
                "Cannot retrieve chunk size of %(bd)r, because no read access to %(file)r.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        f_content = self.read_file(v_file, quiet=True).strip()
        if not f_content:
            msg = _(
                "Cannot retrieve chunk size state of %(bd)r, because file %(file)r has no content.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        self._chunk_size = int(f_content)

    # -------------------------------------------------------------------------
    def retr_state(self):
        """
        A method to retrieve the state of the MD Raid device from sysfs

        @raise MdDeviceError: if the array_size file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve state, because it's an unnamed MD device object.")
            raise MdDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve state of %r, because the MD device doesn't exists.") % (self.name)
            raise MdDeviceError(msg)

        v_file = self.state_file
        if not os.path.exists(v_file):
            msg = _(
                "Cannot retrieve state of %(bd)r, because the file %(file)r doesn't exists.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        if not os.access(v_file, os.R_OK):
            msg = _(
                "Cannot retrieve state of %(bd)r, because no read access to %(file)r.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        f_content = self.read_file(v_file, quiet=True).strip()
        if not f_content:
            msg = _(
                "Cannot retrieve state state of %(bd)r, because file %(file)r has no content.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        self._state = f_content

    # -------------------------------------------------------------------------
    def retr_degraded(self):
        """
        A method to retrieve the degraded state of the MD Raid device from sysfs

        @raise MdDeviceError: if the degraded file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve degraded state, because it's an unnamed MD device object.")
            raise MdDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve degraded state of %r, because the MD device doesn't exists.") % (self.name)
            raise MdDeviceError(msg)

        v_file = self.degraded_file
        if not os.path.exists(v_file):
            msg = _(
                "Cannot retrieve degraded state of %(bd)r, because the file %(file)r doesn't exists.") % {
                'bd': self.name, 'file': v_file}
            if self.verbose > 1:
                LOG.debug(msg)
            self._degraded = None
            return

        if not os.access(v_file, os.R_OK):
            msg = _(
                "Cannot retrieve degraded state of %(bd)r, because no read access to %(file)r.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        f_content = self.read_file(v_file, quiet=True).strip()
        if not f_content:
            msg = _(
                "Cannot retrieve degraded state state of %(bd)r, because file %(file)r has no content.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        self._degraded = True
        if f_content == '0':
            self._degraded = False

    # -------------------------------------------------------------------------
    def retr_raid_disks(self):
        """
        A method to retrieve the number of raid disks of the MD Raid device from sysfs

        @raise MdDeviceError: if the raid_disks file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve the number of raid disks, because it's an unnamed MD device object.")
            raise MdDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve the number of raid disks of %r, because the MD device doesn't exists.") % (self.name)
            raise MdDeviceError(msg)

        v_file = self.raid_disks_file
        if not os.path.exists(v_file):
            msg = _(
                "Cannot retrieve the number of raid disks of %(bd)r, because the file %(file)r doesn't exists.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        if not os.access(v_file, os.R_OK):
            msg = _(
                "Cannot retrieve the number of raid disks of %(bd)r, because no read access to %(file)r.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        f_content = self.read_file(v_file, quiet=True).strip()
        if not f_content:
            msg = _(
                "Cannot retrieve the number of raid disks state of %(bd)r, because file %(file)r has no content.") % {
                'bd': self.name, 'file': v_file}
            raise MdDeviceError(msg)

        self._raid_disks = int(f_content)

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4