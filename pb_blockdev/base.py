#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2013 by Profitbricks GmbH
@license: GPL3
@summary: Module for a base blockdevice class
"""

# Standard modules
import sys
import os
import logging
import re
import glob
import math
import pwd
import grp
import stat

from numbers import Number

# Third party modules

import parted
from parted import IOException

# Own modules
from pb_base.common import pp, bytes2human
from pb_base.common import to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_blockdev.translate import translator

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.6.6'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

base_sysfs_blockdev_dir = os.sep + os.path.join('sys', 'block')
re_major_minor = re.compile('^\s*(\d+):(\d+)')
sector_size = 512

# Refercences:
#
# 1. NIST Special Publication 330, 2008 Edition, Barry N. Taylor and Ambler
#    Thompson, Editors
#    The International System of Units (SI)
#    Available from: http://physics.nist.gov/cuu/pdf/sp811.pdf
#
# 2. International standard IEC 60027-2, third edition,
#    Letter symbols to be used in electrical technology --
#    Part 2: Telecommunications and electronics.
#
# See the links below for quick online summaries:
#
# SI units:  http://physics.nist.gov/cuu/Units/prefixes.html
# IEC units: http://physics.nist.gov/cuu/Units/binary.html
__exponents = {
    "B":    1,         # byte
    "kB":   1000 ** 1, # kilobyte
    "MB":   1000 ** 2, # megabyte
    "GB":   1000 ** 3, # gigabyte
    "TB":   1000 ** 4, # terabyte
    "PB":   1000 ** 5, # petabyte
    "EB":   1000 ** 6, # exabyte
    "ZB":   1000 ** 7, # zettabyte
    "YB":   1000 ** 8, # yottabyte

    "KiB":  1024 ** 1, # kibibyte
    "MiB":  1024 ** 2, # mebibyte
    "GiB":  1024 ** 3, # gibibyte
    "TiB":  1024 ** 4, # tebibyte
    "PiB":  1024 ** 5, # pebibyte
    "EiB":  1024 ** 6, # exbibyte
    "ZiB":  1024 ** 7, # zebibyte
    "YiB":  1024 ** 8  # yobibyte
}

#==============================================================================
class BlockDeviceError(PbBaseHandlerError):
    """
    Base error class for all exceptions belonging to base block device
    """

    pass

#==============================================================================
def format_bytes(bytes_, unit, in_float = False):
    """
    Convert bytes_ using an SI or IEC prefix. Note that unit is a
    case sensitive string that must exactly match one of the IEC or SI
    prefixes followed by 'B' (e.g. 'GB').

    @raise SyntaxError: on a unsupported unit

    @param bytes_: the number of bytes to convert
    @type bytes_: int or long
    @param unit: the unit to convert into
    @type unit: str
    @param in_float: gives the result back as a float value instead of long or int
    @type in_float: bool

    @return: the converted value
    @rtype: int or long or float

    """

    if unit not in __exponents.keys():
        msg = _("%r is not a valid SI or IEC byte unit.") % (unit)
        raise SyntaxError(msg)

    if in_float:
        return float(float(bytes_) / float(__exponents[unit]))
    return (bytes_ / __exponents[unit])

#==============================================================================
def size_to_sectors(bytes_, unit, sector_size = 512):
    """
    Convert bytes_ of unit to a number of sectors. Note that unit is a
    case sensitive string that must exactly match one of the IEC or SI
    prefixes followed by 'B' (e.g. 'GB').
    """

    if unit not in __exponents.keys():
        msg = _("%r is not a valid SI or IEC byte unit.") % (unit)
        raise SyntaxError(msg)

    return bytes_ * __exponents[unit] // sector_size

#==============================================================================
class BlockDeviceStatistic(PbBaseObject):
    """
    Class for encapsulating the statistics of a blockdevice, how read
    from /sys/block/<blockdev>/stat.
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            read_ios = 0L,
            read_merges = 0L,
            read_sectors = 0L,
            read_ticks = 0L,
            write_ios = 0L,
            write_merges = 0L,
            write_sectors = 0L,
            write_ticks = 0L,
            in_flight = 0L,
            io_ticks = 0L,
            time_in_queue = 0L,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            ):
        """
        Initialisation of the BlockDeviceStatistic object.

        @param read_ios: increment when an read request completes.
        @type read_ios: long
        @param read_merges: increment when an read request is merged with an
                            already-queued read request.
        @type read_merges: long
        @param read_sectors: count the number of sectors read from the blockdevice
        @type read_sectors: long
        @param read_ticks: count the number of milliseconds that read requests
                           have waited on this block device.
        @type read_ticks: long
        @param write_ios: increment when an write request completes.
        @type write_ios: long
        @param write_merges: increment when an write request is merged with an
                             alwritey-queued write request.
        @type write_merges: long
        @param write_sectors: count the number of sectors written to the blockdevice
        @type write_sectors: long
        @param write_ticks: count the number of milliseconds that write requests
                            have waited on this block device.
        @type write_ticks: long
        @param in_flight: counts the number of I/O requests that have been
                          issued to the device driver but have not yet completed.
        @type in_flight: long
        @param io_ticks: counts the number of milliseconds during which the
                         device has had I/O requests queued.
        @type io_ticks: long
        @param time_in_queue: counts the number of milliseconds that I/O
                              requests have waited on this block device.
        @type time_in_queue: long
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

        """

        super(BlockDeviceStatistic, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
        )

        self._read_ios = read_ios
        self._read_merges = read_merges
        self._read_sectors = read_sectors
        self._read_ticks = read_ticks
        self._write_ios = write_ios
        self._write_merges = write_merges
        self._write_sectors = write_sectors
        self._write_ticks = write_ticks
        self._in_flight = in_flight
        self._io_ticks = io_ticks
        self._time_in_queue = time_in_queue

        self.initialized = True

    #------------------------------------------------------------
    @property
    def read_ios(self):
        """Number of complete read requests."""
        return self._read_ios

    #------------------------------------------------------------
    @property
    def read_merges(self):
        """Number of merged already-queued read requests."""
        return self._read_merges

    #------------------------------------------------------------
    @property
    def read_sectors(self):
        """Number of sectors read from the blockdevice."""
        return self._read_sectors

    #------------------------------------------------------------
    @property
    def read_ticks(self):
        """Number of milliseconds that read requests have waited."""
        return self._read_ticks

    #------------------------------------------------------------
    @property
    def write_ios(self):
        """Number of complete write requests."""
        return self._write_ios

    #------------------------------------------------------------
    @property
    def write_merges(self):
        """Number of merged alwritey-queued write request."""
        return self._write_merges

    #------------------------------------------------------------
    @property
    def write_sectors(self):
        """Number of sectors written to the blockdevice."""
        return self._write_sectors

    #------------------------------------------------------------
    @property
    def write_ticks(self):
        """Number of milliseconds that write requests have waited."""
        return self._write_ticks

    #------------------------------------------------------------
    @property
    def in_flight(self):
        """Number of I/O requests that have been issued to the device driver
           but have not yet completed."""
        return self._in_flight

    #------------------------------------------------------------
    @property
    def io_ticks(self):
        """Number of milliseconds during which the device has had
           I/O requests queued."""
        return self._io_ticks

    #------------------------------------------------------------
    @property
    def time_in_queue(self):
        """Number of milliseconds that I/O requests have waited
           on this block device."""
        return self._time_in_queue

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(BlockDeviceStatistic, self).as_dict(short = short)
        res['read_ios'] = self.read_ios
        res['read_merges'] = self.read_merges
        res['read_sectors'] = self.read_sectors
        res['read_ticks'] = self.read_ticks
        res['write_ios'] = self.write_ios
        res['write_merges'] = self.write_merges
        res['write_sectors'] = self.write_sectors
        res['write_ticks'] = self.write_ticks
        res['in_flight'] = self.in_flight
        res['io_ticks'] = self.io_ticks
        res['time_in_queue'] = self.time_in_queue

        return res


#==============================================================================
class BlockDevice(PbBaseHandler):
    """
    Base block device object.
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            name,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            simulate = False,
            *targs,
            **kwargs
            ):
        """
        Initialisation of the base blockdevice object.

        @raise CommandNotFoundError: if some needed commands could not be found.
        @raise BlockDeviceError: on a uncoverable error.

        @param name: name of the blockdevice, like used under /sys/block.
        @type name: None (if not even discoverd) or str
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

        @return: None

        """

        super(BlockDevice, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
                simulate = simulate,
                sudo = False,
                quiet = False,
        )

        self._name = name
        """
        @ivar: name of the blockdevice, like used under /sys/block
        @type: None (if not even discoverd) or str
        """

        self._major_number = None
        """
        @ivar: the major device number
        @type: int
        """

        self._minor_number = None
        """
        @ivar: the minor device number
        @type: int
        """

        self._removable = None
        """
        @ivar: flag, whether the device is removeable, e.g. CD-ROM
        @type: bool
        """

        self._readonly = None
        """
        @ivar: flage, whether the device is radonly, e.g. CD-ROM
        @type: bool
        """

        self._sectors = None
        """
        @ivar: size of the blockdevice in 512-byte sectors
        @type: long
        """

        self._holders = None
        """
        @ivar: list of all holders of the current blockdevice (other
               blockdevices, dependend on the current), holders are given
               with their blockdevice names (e.g. 'dm-7').
        @type: tuple of str
        """

        self._slaves = None
        """
        @ivar: list of all slaves of the current blockdevice (other
               blockdevices, from which the current is depending), slaves are
               given with their blockdevice names (e.g. 'sda').
        @type: tuple of str
        """

        self._default_mknod_uid = 0
        """
        @ivar: the default UID of the owning user in case of mknod
               of the device file, defaults to 0 == root
        @type: int
        """

        self._default_mknod_gid = 0
        """
        @ivar: the default GID of the owning group in case of mknod
               of the device file, defaults to 6 == disk
        @type: int
        """
        try:
            self.default_mknod_gid = 'disk'
        except BlockDeviceError, e:
            log.warning(str(e))

        self._default_mknod_mode = (stat.S_IRUSR | stat.S_IWUSR |
                 stat.S_IRGRP | stat.S_IWGRP)
        """
        @ivar: the default creation mode in case of mknod
               of the device file
        @type: int
        """

        self.initialized = True

    #------------------------------------------------------------
    @property
    def name(self):
        """The name of the blockdevice, like used under /sys/block"""
        return getattr(self, '_name', None)

    @name.setter
    def name(self, value):
        if not value:
            msg = _("No new name given.")
            raise BlockDeviceError(msg)
        new_name = str(value).strip()
        if not new_name:
            msg = _("Empty name %r given as name of the blockdevice.") % (
                    value)
            raise BlockDeviceError(msg)
        self._name = new_name

    #------------------------------------------------------------
    @property
    def device(self):
        """The file name of the approriate device file under /dev."""
        if not self.name:
            return None
        return os.sep + os.path.join('dev', self.name)

    #------------------------------------------------------------
    @property
    def sysfs_bd_dir(self):
        """The apropriate directory under /sys/block, e.g. /sys/block/sda"""
        if not self.name:
            return None
        return os.path.join(base_sysfs_blockdev_dir, self.name)

    #------------------------------------------------------------
    @property
    def sysfs_bd_dir_real(self):
        """The real path of the blockdev dir in sysfs"""
        if not self.sysfs_bd_dir:
            return None
        if not os.path.exists(self.sysfs_bd_dir):
            return None
        return os.path.realpath(self.sysfs_bd_dir)

    #------------------------------------------------------------
    @property
    def sysfs_dev_file(self):
        """The file in sysfs containing the major:minor number of the device."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'dev')

    #------------------------------------------------------------
    @property
    def sysfs_removable_file(self):
        """The file in sysfs containing whether the device is removable."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'removable')

    #------------------------------------------------------------
    @property
    def sysfs_ro_file(self):
        """The file in sysfs containing whether the device is readonly."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'ro')

    #------------------------------------------------------------
    @property
    def sysfs_size_file(self):
        """The file in sysfs containing the size in 512-byte sectors."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'size')

    #------------------------------------------------------------
    @property
    def sysfs_stat_file(self):
        """The file in sysfs containing statistic data of the device."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'stat')

    #------------------------------------------------------------
    @property
    def sysfs_holders_dir(self):
        """The directory in sysfs containing holders of the device."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'holders')

    #------------------------------------------------------------
    @property
    def holders(self):
        """A list of all holders of the current blockdevice."""
        if self._holders is not None:
            return self._holders
        if not self.sysfs_holders_dir:
            return None
        if not os.path.exists(self.sysfs_holders_dir):
            return None
        holders = []
        match = os.path.join(self.sysfs_holders_dir, '*')
        holder_files = glob.glob(match)
        if holder_files:
            for holder_file in sorted(holder_files):
                holders.append(os.path.basename(holder_file))
        self._holders = tuple(holders[:])
        return self._holders

    #------------------------------------------------------------
    @property
    def slaves(self):
        """A list of all slaves of the current blockdevice."""
        if self._slaves is not None:
            return self._slaves
        if not self.sysfs_slaves_dir:
            return None
        if not os.path.exists(self.sysfs_slaves_dir):
            return None
        slaves = []
        match = os.path.join(self.sysfs_slaves_dir, '*')
        slave_files = glob.glob(match)
        if slave_files:
            for slave_file in sorted(slave_files):
                slaves.append(os.path.basename(slave_file))
        self._slaves = tuple(slaves[:])
        return self._slaves

    #------------------------------------------------------------
    @property
    def sysfs_slaves_dir(self):
        """The directory in sysfs containing slaves of the device."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'slaves')

    #------------------------------------------------------------
    @property
    def exists(self):
        """Does the blockdevice of the current object exists?"""
        sfs_dir = self.sysfs_bd_dir
        if not sfs_dir:
            return False
        if os.path.exists(sfs_dir):
            return True
        return False

    #------------------------------------------------------------
    @property
    def sectors(self):
        """The size of the blockdevice in 512-byte sectors."""
        if self._sectors is not None:
            return self._sectors
        if not self.exists:
            return None
        self.retr_sectors()
        return self._sectors

    #------------------------------------------------------------
    @property
    def size(self):
        """The size of the blockdevice in bytes."""
        if self.sectors is None:
            return None
        return self.sectors *  long(sector_size)

    #------------------------------------------------------------
    @property
    def major_number(self):
        """The major device number."""
        if self._major_number is not None:
            return self._major_number
        if not self.exists:
            return None
        self.retr_major_minor()
        return self._major_number

    #------------------------------------------------------------
    @property
    def minor_number(self):
        """The minor device number."""
        if self._minor_number is not None:
            return self._minor_number
        if not self.exists:
            return None
        self.retr_major_minor()
        return self._minor_number

    #------------------------------------------------------------
    @property
    def major_minor_number(self):
        """The major and the minor number together."""
        if self.major_number is None or self.minor_number is None:
            return None
        return "%d:%d" % (self.major_number, self.minor_number)

    #------------------------------------------------------------
    @property
    def removable(self):
        """A flag, whether the device is removeable, e.g. CD-ROM."""
        if self._removable is not None:
            return self._removable
        if not self.exists:
            return None
        self.retr_removable()
        return self._removable

    #------------------------------------------------------------
    @property
    def readonly(self):
        """A flag, whether the device is readonly, e.g. CD-ROM."""
        if self._readonly is not None:
            return self._readonly
        if not self.exists:
            return None
        self.retr_readonly()
        return self._readonly

    #------------------------------------------------------------
    @property
    def default_mknod_uid(self):
        """The default UID of the owning user in case of mknod."""
        return self._default_mknod_uid

    @default_mknod_uid.setter
    def default_mknod_uid(self, value):
        uid = self._default_mknod_uid
        if isinstance(value, Number):
            uid = abs(int(value))
        elif isinstance(value, str):
            user = None
            try:
                user = pwd.getpwnam(value)
            except KeyError, e:
                msg = _("Username %r not found in system.") % (value)
                raise BlockDeviceError(msg)
            uid = user.pw_uid
        else:
            msg = _("Invalid value %r as user id given.") % (value)
            raise BlockDeviceError(msg)

        self._default_mknod_uid = uid

    #------------------------------------------------------------
    @property
    def default_mknod_gid(self):
        """The default GID of the owning group in case of mknod."""
        return self._default_mknod_gid

    @default_mknod_gid.setter
    def default_mknod_gid(self, value):
        gid = self._default_mknod_gid
        if isinstance(value, Number):
            gid = abs(int(value))
        elif isinstance(value, str):
            group = None
            try:
                group = grp.getgrnam(value)
            except KeyError, e:
                msg = _("Group name %r not found in system.") % (value)
                raise BlockDeviceError(msg)
            gid = group.gr_gid
        else:
            msg = _("Invalid value %r as group id given.") % (value)
            raise BlockDeviceError(msg)

        self._default_mknod_gid = gid

    #------------------------------------------------------------
    @property
    def default_mknod_mode(self):
        """The default creation mode in case of mknod of the device file."""
        return self._default_mknod_mode

    @default_mknod_mode.setter
    def default_mknod_mode(self, value):
        self._default_mknod_mode = abs(int(value))

    #--------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable block device.

        @raise BlockDeviceError: if the given device name is invalid,
                                 e.g. has path parts

        @param device_name: the basename of the blockdevice to check, e.g. 'sda'
                            or 'dm-7' or 'loop0' or 'md0'
        @type device_name: str

        @return: the given device name is usable as a blockdevice name and exists.
        @rtype: bool

        """

        if not device_name:
            raise BlockDeviceError(_("No device name given."))
        if device_name != os.path.basename(device_name):
            msg  = _("Invalid device name %r given.") % (device_name)
            raise BlockDeviceError(msg)

        bd_dir = os.sep + os.path.join('sys', 'block', device_name)
        if os.path.exists(bd_dir):
            return True
        return False

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(BlockDevice, self).as_dict(short = short)
        res['name'] = self.name
        res['device'] = self.device
        res['sysfs_bd_dir'] = self.sysfs_bd_dir
        res['sysfs_bd_dir_real'] = self.sysfs_bd_dir_real
        res['sysfs_dev_file'] = self.sysfs_dev_file
        res['sysfs_removable_file'] = self.sysfs_removable_file
        res['sysfs_ro_file'] = self.sysfs_ro_file
        res['sysfs_size_file'] = self.sysfs_size_file
        res['sysfs_stat_file'] = self.sysfs_stat_file
        res['sysfs_holders_dir'] = self.sysfs_holders_dir
        res['sysfs_slaves_dir'] = self.sysfs_slaves_dir
        res['exists'] = self.exists
        res['holders'] = self.holders
        res['slaves'] = self.slaves
        res['sectors'] = self.sectors
        res['size'] = self.size
        res['removable'] = self.removable
        res['readonly'] = self.readonly
        res['major_number'] = self.major_number
        res['minor_number'] = self.minor_number
        res['major_minor_number'] = self.major_minor_number
        res['default_mknod_uid'] = self.default_mknod_uid
        res['default_mknod_gid'] = self.default_mknod_gid
        res['default_mknod_mode'] = oct(self.default_mknod_mode)

        return res

    #--------------------------------------------------------------------------
    def get_statistics(self):
        """
        Retrieve blockdevice statistics data from the stat file.

        @raise BlockDeviceError: if the stat file in sysfs doesn't exists
                                 or could not read

        @return: a BlockDeviceStatistic object containing all data
                 from the statistics file.
        @rtype: BlockDeviceStatistic

        """

        if not self.name:
            msg = _("Cannot retrieve statistics, because it's an unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve statistics of %r, because the block device doesn't exists.") % (
                    self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_stat_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve statistics of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve statistics of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve statistics of %(bd)r, because file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        fields = f_content.split()
        stats = BlockDeviceStatistic(
                read_ios = long(fields[0]),
                read_merges = long(fields[1]),
                read_sectors = long(fields[2]),
                read_ticks = long(fields[3]),
                write_ios = long(fields[4]),
                write_merges = long(fields[5]),
                write_sectors = long(fields[6]),
                write_ticks = long(fields[7]),
                in_flight = long(fields[8]),
                io_ticks = long(fields[9]),
                time_in_queue = long(fields[10]),
                appname = self.appname,
                verbose = self.verbose,
                base_dir = self.base_dir,
                use_stderr = self.use_stderr,
        )

        return stats

    #--------------------------------------------------------------------------
    def retr_removable(self):
        """
        A method to retrieve whether the device is a removable device.

        @raise BlockDeviceError: if the removable file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve removable state, because it's an unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve removable state of %r, because the block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_removable_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve removable state of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve removable state of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve removable state of %(bd)r, because file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if f_content == '1':
            self._removable = True
        else:
            self._removable = False

    #--------------------------------------------------------------------------
    def retr_readonly(self):
        """
        A method to retrieve whether the device is a readonly device.

        @raise BlockDeviceError: if the readonly file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve readonly state, because it's an unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve readonly state of %r, because the block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_ro_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve readonly state of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve readonly state of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve readonly state of %(bd)r, because file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if f_content == '1':
            self._readonly = True
        else:
            self._readonly = False

    #--------------------------------------------------------------------------
    def retr_sectors(self):
        """
        A method to retrieve the size of the blockdevice in 512-byte sectors.

        @raise BlockDeviceError: if the size file in sysfs doesn't exits
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve size, because it's an unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve size of %r, because the block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_size_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve size of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve size of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve size of %(bd)r, because file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        try:
            self._sectors = long(f_content)
        except ValueError, e:
            msg = _("Cannot retrieve size of %(bd)r, because file %(file)r has illegal content: %(err)s") % {
                    'bd': self.name, 'file': r_file, 'err': str(e)}
            raise BlockDeviceError(msg)

    #--------------------------------------------------------------------------
    def retr_major_minor(self):
        """
        A method to retrieve the major/minor number of the device form the
        appropriate dev file in sysfs. These numbers are saved in
        self._major_number and self._minor_number.

        @raise BlockDeviceError: if the dev file in sysfs doesn't exits
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve major/minor number, because it's an unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve major/minor number of %r, because the block device doesn't exists.") % (
                    self.name)
            raise BlockDeviceError(msg)

        dev_file = self.sysfs_dev_file
        if not os.path.exists(dev_file):
            msg = _("Cannot retrieve major/minor number of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        if not os.access(dev_file, os.R_OK):
            msg = _("Cannot retrieve major/minor number of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(dev_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve major/minor number of %(bd)r, because file %(file)r has no content.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        match = re_major_minor.search(f_content)
        if not match:
            msg = _("Cannot retrieve major/minor number of %(bd)r, because cannot evaluate content of %(file)r: %(cont)r") % {
                    'bd': self.name, 'file': dev_file, 'cont': f_content}
            raise BlockDeviceError(msg)

        self._major_number = int(match.group(1))
        self._minor_number = int(match.group(2))

    #--------------------------------------------------------------------------
    def wipe(self, blocksize = (1024 * 1024)):
        """
        Dumping blocks of binary zeroes into the device.

        @raise BlockDeviceError: if the device doesn't exists
        @raise PbBaseHandlerError: on some error.

        @param blocksize: the blocksize for the dumping action
        @type blocksize: int

        @return: success of dumping
        @rtype: bool

        """

        if not self.exists:
            msg = _("Block device %r to wipe doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        dev = self.device
        if not os.path.exists(dev):
            msg = _("Block device %r to wipe doesn't exists.") % (dev)
            raise BlockDeviceError(msg)

        count = int(math.ceil(float(self.size) / float(blocksize)))

        log.info(_("Wiping %(dev)r by writing %(count)d blocks of %(bs)s binary zeroes ...") % {
                'dev': dev, 'count': count, 'bs': bytes2human(blocksize)})

        return self.dump_zeroes(target = dev, blocksize = blocksize)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
