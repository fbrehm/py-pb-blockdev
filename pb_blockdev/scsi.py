#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a common SCSI device class
"""

# Standard modules
import sys
import os
import logging
import re
import glob
import time

from gettext import gettext as _

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDevice

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

#==============================================================================
class ScsiDeviceError(BlockDeviceError):
    """
    Base error class for all exceptions belonging to common SCSI device
    """

    pass

#==============================================================================
class ScsiDevice(BlockDevice):

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
        Initialisation of the common SCSI device object.

        @raise ScsiDeviceError: on a uncoverable error.

        @param name: name of the SCSI device, e.g. 'sda'
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

        super(ScsiDevice, self).__init__(
                name = name,
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                simulate = simulate,
        )

        self._scsi_host_id = None
        """
        @ivar: The Id of the SCSI host (the SCSI host adater, from HBTL schema)
        @type: int
        """

        self._scsi_bus_id = None
        """
        @ivar: The Id of the SCSI bus (the channel number from HBTL schema)
        @type: int
        """

        self._scsi_target_id = None
        """
        @ivar: The Id of the SCSI target (the target id from HBTL schema)
        @type: int
        """

        self._scsi_lun_id = None
        """
        @ivar: The Id of the SCSI LUN (the lun id from HBTL schema)
        @type: int
        """

        if self.sysfs_device_dir:
            self._get_hbtl_numbers()

    #------------------------------------------------------------
    @property
    def scsi_host_id(self):
        """The Id of the SCSI host
        (the SCSI host adater, from HBTL schema."""
        return self._scsi_host_id

    #------------------------------------------------------------
    @property
    def scsi_bus_id(self):
        """The Id of the SCSI bus
        (the SCSI channel number, from HBTL schema."""
        return self._scsi_bus_id

    #------------------------------------------------------------
    @property
    def scsi_target_id(self):
        """The Id of the SCSI target
        (the SCSI target, from HBTL schema."""
        return self._scsi_target_id

    #------------------------------------------------------------
    @property
    def scsi_lun_id(self):
        """The Id of the SCSI LUN
        (the SCSI lun id from HBTL schema."""
        return self._scsi_lun_id

    #------------------------------------------------------------
    @property
    def hbtl(self):
        """The complete SCSI address in H:B:T:L format."""
        if self.scsi_host_id is None:
            return None
        if self.scsi_bus_id is None:
            return None
        if self.scsi_target_id is None:
            return None
        if self.scsi_lun_id is None:
            return None

        return "%d:%d:%d:%d" % (self.scsi_host_id, self.scsi_bus_id,
                self.scsi_target_id, self.scsi_lun_id)

    #------------------------------------------------------------
    @property
    def sysfs_device_dir(self):
        """The device directory under /sys/block, e.g. /sys/block/sda/device"""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'device')

    #------------------------------------------------------------
    @property
    def sysfs_device_dir_real(self):
        """The real path of the device directory in sysfs."""
        if not self.sysfs_device_dir:
            return None
        if not os.path.exists(self.sysfs_device_dir):
            return None
        return os.path.realpath(self.sysfs_device_dir)

    #------------------------------------------------------------
    @property
    def sysfs_scsi_device_dir(self):
        """The device directory under /sys/block,
           e.g. /sys/block/sda/device/scsi_device"""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'scsi_device')

    #------------------------------------------------------------
    @property
    def sysfs_scsi_device_dir_real(self):
        """The real path of the scsi_device directory in sysfs."""
        if not self.sysfs_scsi_device_dir:
            return None
        if not os.path.exists(self.sysfs_scsi_device_dir):
            return None
        return os.path.realpath(self.sysfs_scsi_device_dir)

    #------------------------------------------------------------
    @property
    def delete_file(self):
        """The path to the delete file in sysfs for deleting the SCSI device."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'delete')

    #------------------------------------------------------------
    @property
    def device_blocked_file(self):
        """The path to the device_blocked file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'device_blocked')

    #------------------------------------------------------------
    @property
    def modalias_file(self):
        """The path to the modalias file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'modalias')

    #------------------------------------------------------------
    @property
    def model_file(self):
        """The path to the model file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'model')

    #------------------------------------------------------------
    @property
    def queue_depth_file(self):
        """The path to the queue_depth file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'queue_depth')

    #------------------------------------------------------------
    @property
    def queue_ramp_up_period_file(self):
        """The path to the queue_ramp_up_period file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'queue_ramp_up_period')

    #------------------------------------------------------------
    @property
    def queue_type_file(self):
        """The path to the queue_type file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'queue_type')

    #------------------------------------------------------------
    @property
    def rescan_file(self):
        """The path to the rescan file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'rescan')

    #------------------------------------------------------------
    @property
    def rev_file(self):
        """The path to the rev file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'rev')

    #------------------------------------------------------------
    @property
    def scsi_level_file(self):
        """The path to the scsi_level file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'scsi_level')

    #------------------------------------------------------------
    @property
    def state_file(self):
        """The path to the state file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'state')

    #------------------------------------------------------------
    @property
    def timeout_file(self):
        """The path to the timeout file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'timeout')

    #------------------------------------------------------------
    @property
    def type_file(self):
        """The path to the type file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'type')

    #------------------------------------------------------------
    @property
    def vendor_file(self):
        """The path to the vendor file in sysfs."""
        if not self.sysfs_device_dir:
            return None
        return os.path.join(self.sysfs_device_dir, 'vendor')

    #--------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable SCSI device.

        @raise ScsiDeviceError: if the given device name is invalid,
                                e.g. has path parts

        @param device_name: the basename of the loop device to check, e.g. 'sda'
        @type device_name: str

        @return: the given device name is usable as a SCSI device name and exists.
        @rtype: bool

        """

        if not device_name:
            raise ScsiDeviceError(_("No device name given."))
        if device_name != os.path.basename(device_name):
            msg  = _("Invalid device name %r given.") % (device_name)
            raise ScsiDeviceError(msg)

        bd_dir = os.sep + os.path.join('sys', 'block', device_name)
        if not os.path.exists(bd_dir):
            return False

        dev_dir = os.path.join(bd_dir, 'device')
        if not os.path.exists(dev_dir):
            return False
        if not os.access(dev_dir, os.R_OK):
            log.warn(_("No read access to %r."), dev_dir)
            return False

        scsi_device_dir = os.path.join(dev_dir, 'scsi_device')
        if not os.path.exists(scsi_device_dir):
            return False
        if not os.access(scsi_device_dir, os.R_OK):
            log.warn(_("No read access to %r."), scsi_device_dir)
            return False

        return True

    #--------------------------------------------------------------------------
    def _get_hbtl_numbers(self):
        """
        Trying to retrieve the H:B:T:L numbers of the current SCSI device.

        @raise ScsiDeviceError: if H:B:T:L numbers could not retrieved.

        """

        if not self.sysfs_scsi_device_dir:
            msg  = _("Directory %s not found.") % (self.sysfs_scsi_device_dir)
            raise ScsiDeviceError(msg)

        if (self.scsi_host_id is not None and self.scsi_bus_id is not None and
                self.scsi_target_id is not None and self.scsi_lun_id is not None):
            return None

        try_no = 0
        pattern = os.path.join(self.sysfs_scsi_device_dir, '*:*:*:*')
        if self.verbose > 2:
            log.debug(_("Search pattern: %r"), pattern)
        while try_no < 10:
            try_no += 1
            log.debug(_("Try %d to retrieve the H:B:T:L numbers of the " +
                    "current SCSI device %s ..."), try_no, self.device)
            dirs = glob.glob(pattern)
            if dirs:
                hbtl = os.path.basename(dirs[0])
                log.debug(_("Found H:B:T:L numbers %r."), hbtl)
                numbers = map(lambda x: int(x), hbtl.split(':'))
                self._scsi_host_id = numbers[0]
                self._scsi_bus_id = numbers[1]
                self._scsi_target_id = numbers[2]
                self._scsi_lun_id = numbers[3]
                return

            time.sleep(0.05)

        msg  = _("Could not retrieve H:B:T:L numbers of the current " +
                "SCSI device %s.") % (self.device)
        raise ScsiDeviceError(msg)
        return

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(ScsiDevice, self).as_dict()
        res['sysfs_device_dir'] = self.sysfs_device_dir
        res['sysfs_device_dir_real'] = self.sysfs_device_dir_real
        res['sysfs_scsi_device_dir'] = self.sysfs_scsi_device_dir
        res['sysfs_scsi_device_dir_real'] = self.sysfs_scsi_device_dir_real
        res['delete_file'] = self.delete_file
        res['device_blocked_file'] = self.device_blocked_file
        res['modalias_file'] = self.modalias_file
        res['model_file'] = self.model_file
        res['queue_depth_file'] = self.queue_depth_file
        res['queue_ramp_up_period_file'] = self.queue_ramp_up_period_file
        res['queue_type_file'] = self.queue_type_file
        res['rescan_file'] = self.rescan_file
        res['rev_file'] = self.rev_file
        res['scsi_level_file'] = self.scsi_level_file
        res['state_file'] = self.state_file
        res['timeout_file'] = self.timeout_file
        res['type_file'] = self.type_file
        res['vendor_file'] = self.vendor_file
        res['scsi_host_id'] = self.scsi_host_id
        res['scsi_bus_id'] = self.scsi_bus_id
        res['scsi_target_id'] = self.scsi_target_id
        res['scsi_lun_id'] = self.scsi_lun_id
        res['hbtl'] = self.hbtl

        return res

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
