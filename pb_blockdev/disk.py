#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2014 by Profitbricks GmbH
@license: GPL3
@summary: Module for a class for partitioned Disk
"""

# Standard modules
import sys
import os
import logging
import re
import glob
import time

# Third party modules

import parted
from parted import IOException

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDevice

from pb_blockdev.translate import translator, pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.2.8'

log = logging.getLogger(__name__)

# --------------------------------------------
# Some module variables

VALID_DISK_UNIT_MODES = ('BYT', 'CHS', 'CYL')

PED_DEVICE_TYPES = {
    0: 'unknown',
    1: 'scsi',
    2: 'ide',
    4: 'cpqarray',
    5: 'file',
    6: 'ataraid',
    7: 'i20',
    8: 'ubd',
    9: 'dasd',
    10: 'viodasd',
    11: 'sx8',
    12: 'dm',
    13: 'xvd',
    14: 'sdmmc',
    15: 'virtblk',
    16: 'aoe',
    17: 'md',
    18: 'loop',
}


# =============================================================================
class DiskError(BlockDeviceError):
    """
    Base error class for all exceptions belonging to the disk module
    """

    pass


# =============================================================================
class DiskNotDiscoveredError(DiskError):
    """
    Special exception class in case, if it is not possible to discover it.
    """

    # -------------------------------------------------------------------------
    def __init__(self, disk, reason=None):
        """
        Constructor.

        @param disk: the name of the disk, which could not discovered.
        @type disk: str
        @param reason: the reason, why the disk could not discovered.
        @type reason: str

        """

        self.disk = str(disk).strip()
        if not self.disk:
            self.disk = _("Unknown disk")

        self.reason = None
        if reason:
            self.reason = str(reason).strip()
        if not self.reason:
            self.reason = _("Unknown reason")

    # -------------------------------------------------------------------------
    def __str__(self):

        msg = _("Could not discover disk %r:") % (self.disk)
        msg += ' ' + self.reason
        return msg


# =============================================================================
class Disk(BlockDevice):
    """
    A class for encapsulating a partitioned disk (HD or such similar).
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, name, auto_discover=False, appname=None, verbose=0,
            version=__version__, base_dir=None, use_stderr=False,
            simulate=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the partitioned disk object.

        @raise DiskError: on a uncoverable error.

        @param name: name of the disk, e.g. 'sda'
        @type name: None (if not even discoverd) or str
        @param auto_discover: automatic discovering of partitions
                              after initialization
        @type auto_discover: bool
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

        super(Disk, self).__init__(
            name=name,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            simulate=simulate,
            initialized=False,
        )
        self.initialized = False

        self._disk_discovered = False
        """
        @ivar: flag, whether the disk was discovered via 'parted'
        @type: bool
        """

        self._auto_discover = bool(auto_discover)
        """
        @ivar: automatic discovering of partitions after initialization
        @type: bool
        """

        self._discoverable = None
        """
        @ivar: flag, that the disk could be discoverd somehow or not
        @type: bool
        """

        self.partitions = []
        """
        @ivar: a list with all partition objects
        @type: list of Partition objects
        """

        self._blocks = None
        """
        @ivar: The number of logical blocks of the disk.
        @type: long
        """

        self._type = None
        """
        @ivar: the transport type of the disk according
               to the ped.PED_DEVICE* constants
        @type: int
        """

        self._bs_logical = None
        """
        @ivar: the logical sector size of the disk
        @type: int
        """

        self._bs_physical = None
        """
        @ivar: the physical sector size of the disk
        @type: int
        """

        self._partition_table_type = None
        """
        @ivar: the type of the current partition table
        @type: str
        """

        self._model_name = None
        """
        @ivar: The model name like given by 'parted -m print'
        @type: str
        """

        self.parted_device = None
        """
        @ivar: a device object to execute all parted methods
        @type: parted.Device or None
        """

        self.parted_disk = None
        """
        @ivar: a disk (partition table) object to execute all parted methods
        @type: parted.Disk or None
        """

        self._hw_geometry = None
        """
        @ivar: the hardware geometry of this device.
        @type: a 3-tuple in order of cylinders, heads, and sectors.
        """

        self._bios_geometry = None
        """
        @ivar: the BIOS geometry of this device.
        @type: a 3-tuple in order of cylinders, heads, and sectors.
        """

        if self.auto_discover:
            self.discover()

        self.initialized = True

    # -----------------------------------------------------------
    @property
    def disk_discovered(self):
        """A flag, whether the disk was discovered via 'parted'."""
        return self._disk_discovered

    # -----------------------------------------------------------
    @property
    def auto_discover(self):
        """Execute automatic discovering of partitions after initialization."""
        return self._auto_discover

    # -----------------------------------------------------------
    @property
    def discoverable(self):
        """A flag, that the disk could be discoverd somehow or not."""
        return self._discoverable

    # -----------------------------------------------------------
    @property
    def blocks(self):
        """The number of logical blocks of the disk."""
        return self._blocks

    # -----------------------------------------------------------
    @property
    def type(self):
        """
        The transport type of the disk according
        to the ped.PED_DEVICE* constants as an integer value.
        """
        return self._type

    # -----------------------------------------------------------
    @property
    def type_str(self):
        """A str representation of self.type."""
        if self.type is None:
            return None
        if self.type not in PED_DEVICE_TYPES:
            return '<unknown>'
        return PED_DEVICE_TYPES[self.type]

    # -----------------------------------------------------------
    @property
    def bs_logical(self):
        """The logical sector size of the disk."""
        return self._bs_logical

    # -----------------------------------------------------------
    @property
    def bs_physical(self):
        """The physical sector size of the disk."""
        return self._bs_physical

    # -----------------------------------------------------------
    @property
    def partition_table_type(self):
        """The type of the current partition table."""
        return self._partition_table_type

    # -----------------------------------------------------------
    @property
    def model_name(self):
        """The model name like given by 'parted -m print'."""
        return self._model_name

    # -----------------------------------------------------------
    @property
    def disk_size(self):
        """The total size of the partitioned disk in Byte."""
        if self.bs_logical is None or self.blocks is None:
            return None
        if sys.version_info[0] > 2:
            return (int(self.bs_logical) * int(self.blocks))
        return (long(self.bs_logical) * long(self.blocks))

    # -----------------------------------------------------------
    @property
    def disk_size_mb(self):
        """The total size of the partitioned disk in MiByte."""
        if self.disk_size is None:
            return None
        if sys.version_info[0] > 2:
            return self.disk_size / 1024 / 1024
        return self.disk_size / long(1024) / long(1024)

    # -----------------------------------------------------------
    @property
    def disk_size_gb(self):
        """The total size of the partitioned disk in GiByte."""
        if self.disk_size_mb is None:
            return None
        return float(self.disk_size_mb) / 1024.0

    # -----------------------------------------------------------
    @property
    def hw_geometry(self):
        """
        The hardware geometry of this device as a
        3-tuple in order of cylinders, heads, and sectors.
        """
        return self._hw_geometry

    # -----------------------------------------------------------
    @property
    def bios_geometry(self):
        """
        The BIOS geometry of this device as a
        3-tuple in order of cylinders, heads, and sectors.
        """
        return self._bios_geometry

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(Disk, self).as_dict(short=short)
        res['disk_discovered'] = self.disk_discovered
        res['auto_discover'] = self.auto_discover
        res['discoverable'] = self.discoverable
        res['blocks'] = self.blocks
        res['type'] = self.type
        res['type_str'] = self.type_str
        res['bs_logical'] = self.bs_logical
        res['bs_physical'] = self.bs_physical
        res['partition_table_type'] = self.partition_table_type
        res['model_name'] = self.model_name
        res['disk_size'] = self.disk_size
        res['disk_size_mb'] = self.disk_size_mb
        res['disk_size_gb'] = self.disk_size_gb
        res['hw_geometry'] = self.hw_geometry
        res['bios_geometry'] = self.bios_geometry
        res['parted_device'] = None
        if self.parted_device:
            res['parted_device'] = str(self.parted_device)
        res['parted_disk'] = None
        if self.parted_disk:
            res['parted_disk'] = str(self.parted_disk)
        res['partitions'] = []
#        for partition in self.partitions:
#            res['partitions'].append(partition.as_dict(short))

        return res

    # -------------------------------------------------------------------------
    def discover(self, force=False):
        """
        Discovers the current disk. It is not executed, if it seems to be
        allready discovered.

        @raise DiskNotDiscoveredError: if the disk could not discovered.

        @param force: discover the disk, also if it seems to be
                      allready discovered.
        @type force: bool

        """

        if self.disk_discovered and not force:
            if self.verbose > 2:
                log.debug(_("Disk %r is even discovered."), self.name)
            return

        # Reset all properties
        self.parted_device = None
        self.parted_disk = None
        self._blocks = None
        self._bs_logical = None
        self._bs_physical = None
        self._type = None
        self._model_name = None
        self._hw_geometry = None
        self._bios_geometry = None
        self.partitions = []

        if not self.exists:
            self._discoverable = False
            raise DiskNotDiscoveredError(
                self.name, (
                    _("Directory %r doesn't exists.") % (self.sysfs_bd_dir)))

        log.debug(_("Discovery of disk %r ..."), self.name)
        try:
            self.parted_device = parted.Device(self.device)
        except IOException as e:
            self.parted_device = None
            self._discoverable = False
            raise DiskNotDiscoveredError(self.name, str(e))

        try:
            self.parted_disk = parted.Disk(device=self.parted_device)
        except Exception as e:
            self.parted_device = None
            self.parted_disk = None
            self._discoverable = False
            self.handle_error(
                error_message=str(e),
                exception_name=e.__class__.__name__,
                do_traceback=True)
            raise DiskNotDiscoveredError(self.name, str(e))

        self._discoverable = True
        self._blocks = self.parted_device.getLength()
        self._bs_logical = self.parted_device.sectorSize
        self._bs_physical = self.parted_device.physicalSectorSize
        self._type = self.parted_device.type
        if self._type is not None:
            self._type = int(self.type)
        self._model_name = self.parted_device.model
        self._hw_geometry = self.parted_device.hardwareGeometry
        self._bios_geometry = self.parted_device.biosGeometry

        self._disk_discovered = True

        return


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
