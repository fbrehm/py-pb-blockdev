#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a base blockdevice class
"""

# Standard modules
import sys
import os
import logging
import re

from gettext import gettext as _

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

__version__ = '0.5.0'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

base_sysfs_blockdev_dir = os.sep + os.path.join('sys', 'block')
re_major_minor = re.compile('^\s*(\d+):(\d+)')
sector_size = 512

#==============================================================================
class BlockDeviceError(PbBaseHandlerError):
    """
    Base error class for all exceptions belonging to base block device
    """

    pass

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
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(BlockDeviceStatistic, self).as_dict()
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
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(BlockDevice, self).as_dict()
        res['name'] = self.name
        res['device'] = self.device
        res['sysfs_bd_dir'] = self.sysfs_bd_dir
        res['sysfs_bd_dir_real'] = self.sysfs_bd_dir_real
        res['sysfs_dev_file'] = self.sysfs_dev_file
        res['sysfs_removable_file'] = self.sysfs_removable_file
        res['sysfs_ro_file'] = self.sysfs_ro_file
        res['sysfs_size_file'] = self.sysfs_size_file
        res['sysfs_stat_file'] = self.sysfs_stat_file
        res['exists'] = self.exists
        res['sectors'] = self.sectors
        res['size'] = self.size
        res['removable'] = self.removable
        res['readonly'] = self.readonly
        res['major_number'] = self.major_number
        res['minor_number'] = self.minor_number
        res['major_minor_number'] = self.major_minor_number

        return res

    #--------------------------------------------------------------------------
    def get_statistics(self):
        """
        Retrieve blockdevice statistics data from the stat file.

        @raise BlockDeviceError: if the stat file in sysfs doesn't exits
                                 or could not read

        @return: a BlockDeviceStatistic object containing all data
                 from the statistics file.
        @rtype: BlockDeviceStatistic

        """

        if not self.name:
            msg = _("Cannot retrieve statistics, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve statistics of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_stat_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve statistics of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve statistics of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve statistics of %(bd)r, because " +
                    "file %(file)r has no content.") % {
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

        @raise BlockDeviceError: if the removable file in sysfs doesn't exits
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve removable state, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve removable state of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_removable_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve removable state of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve removable state of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve removable state of %(bd)r, because " +
                    "file %(file)r has no content.") % {
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

        @raise BlockDeviceError: if the readonly file in sysfs doesn't exits
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve readonly state, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve readonly state of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_ro_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve readonly state of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve readonly state of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve readonly state of %(bd)r, because " +
                    "file %(file)r has no content.") % {
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
            msg = _("Cannot retrieve size, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve size of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_size_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve size of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve size of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve size of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        try:
            self._sectors = long(f_content)
        except ValueError, e:
            msg = _("Cannot retrieve size of %(bd)r, because " +
                    "file %(file)r has illegal content: %(err)s") % {
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
            msg = _("Cannot retrieve major/minor number, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve major/minor number of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        dev_file = self.sysfs_dev_file
        if not os.path.exists(dev_file):
            msg = _("Cannot retrieve major/minor number of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        if not os.access(dev_file, os.R_OK):
            msg = _("Cannot retrieve major/minor number of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(dev_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve major/minor number of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        match = re_major_minor.search(f_content)
        if not match:
            msg = _("Cannot retrieve major/minor number of %(bd)r, bacause " +
                    "cannot evaluate content of %(file)r: %(cont)r") % {
                    'bd': self.name, 'file': dev_file, 'cont': f_content}
            raise BlockDeviceError(msg)

        self._major_number = int(match.group(1))
        self._minor_number = int(match.group(2))

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
