#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a devicemapper device class
"""

# Standard modules
import sys
import os
import logging
import re
import glob

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

__version__ = '0.1.1'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

DMSETUP_CMD = os.sep + os.path.join('sbin', 'dmsetup')

#==============================================================================
class DmDeviceError(BlockDeviceError):
    """
    Base error class for all exceptions belonging to devicemapper device
    """

    pass

#==============================================================================
class DmDeviceInitError(DmDeviceError):
    """
    Error class for exceptions happening on initialisation of
    a DeviceMapperDevice object.
    """

    pass

#==============================================================================
class DeviceMapperDevice(BlockDevice):

    #--------------------------------------------------------------------------
    def __init__(self,
            name = None,
            dm_name = None,
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
        Initialisation of the devicemapper device object.

        One of parameters 'name' or 'dm_name' must be given to initialize
        the object.

        @raise CommandNotFoundError: if some needed commands could not be found.
        @raise DmDeviceInitError: on a uncoverable error.

        @param name: name of the loop device, e.g. 'dm-1'
        @type name: None (if not even discoverd) or str
        @param dm_name: the devicemapper name
        @type dm_name: str or None
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

        # Normalisation of 'name' and 'dm_name'
        if name is not None:
            name = str(name).strip()

        if dm_name is not None:
            dm_name = str(dm_name).strip()

        # One of those two parameters must be valid:
        if not name and not dm_name:
            msg = _("In minimum one parameter of 'name' and 'dm_name' must " +
                    "be given on initialisation of a DeviceMapperObject.")
            raise DmDeviceInitError(msg)

        super(DeviceMapperDevice, self).__init__(
                name = name,
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                simulate = simulate,
        )

        failed_commands = []

        self._dmsetup_cmd = DMSETUP_CMD
        """
        @ivar: the dmsetup command for manipulating the devicemapper device
        @type: str
        """
        if not os.path.exists(self.dmsetup_cmd) or not os.access(
                self.dmsetup_cmd, os.X_OK):
            self._dmsetup_cmd = self.get_command('dmsetup')
        if not self.dmsetup_cmd:
            failed_commands.append('dmsetup')

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        self.initialized = True
        if self.verbose > 3:
            log.debug(_("Initialized."))

    #------------------------------------------------------------
    @property
    def dmsetup_cmd(self):
        """The absolute path to the OS command 'dmsetup'."""
        return self._dmsetup_cmd

    #------------------------------------------------------------
    @property
    def sysfs_dm_dir(self):
        """
        The directory in sysfs containing devicemapper
        informations of the device.
        """
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'dm')

    #--------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable devicemapper device.

        @raise DmDeviceError: if the given device name is invalid,
                              e.g. has path parts

        @param device_name: the basename of the loop device to check, e.g. 'dm-1'
        @type device_name: str

        @return: the given device name is usable as a devicemapper device name
                 and exists.
        @rtype: bool

        """

        if not device_name:
            raise DmDeviceError(_("No device name given."))
        if device_name != os.path.basename(device_name):
            msg  = _("Invalid device name %r given.") % (device_name)
            raise DmDeviceError(msg)

        bd_dir = os.sep + os.path.join('sys', 'block', device_name)
        if not os.path.exists(bd_dir):
            return False

        dm_dir = os.path.join(bd_dir, 'dm')
        if not os.path.exists(dm_dir):
            return False

        return True

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(DeviceMapperDevice, self).as_dict()
        res['dmsetup_cmd'] = self.dmsetup_cmd
        res['sysfs_dm_dir'] = self.sysfs_dm_dir

        return res


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
