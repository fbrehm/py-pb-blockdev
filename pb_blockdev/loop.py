#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a loop device class
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

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

LOSETUP_CMD = os.sep + os.path.join('sbin', 'losetup')

#==============================================================================
class LoopDeviceError(BlockDeviceError):
    """
    Base error class for all exceptions belonging to base block device
    """

    pass

#==============================================================================
class LoopDevice(BlockDevice):

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
        Initialisation of the base loopdevice object.

        @raise CommandNotFoundError: if some needed commands could not be found.
        @raise LoopDeviceError: on a uncoverable error.

        @param name: name of the loop device, e.g. 'loop0'
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

        super(LoopDevice, self).__init__(
                name = name,
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                simulate = simulate,
        )

        failed_commands = []

        self._losetup_cmd = LOSETUP_CMD
        """
        @ivar: the losetup command for manipulating the loop device
        @type: str
        """
        if not os.path.exists(self.losetup_cmd) or not os.access(
                self.losetup_cmd, os.X_OK):
            self._losetup_cmd = self.get_command('losetup')
        if not self.losetup_cmd:
            failed_commands.append('losetup')

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        self.initialized = True
        if self.verbose > 3:
            log.debug(_("Initialized."))

    #------------------------------------------------------------
    @property
    def losetup_cmd(self):
        """The absolute path to the OS command 'losetup'."""
        return self._losetup_cmd

    #--------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable loop device.

        @raise LoopDeviceError: if the given device name is invalid,
                                e.g. has path parts

        @param device_name: the basename of the loop device to check, e.g. 'loop0'
        @type device_name: str

        @return: the given device name is usable as a loop device name and exists.
        @rtype: bool

        """

        if not super(LoopDevice, self).isa(device_name):
            return False

        dev_file = os.sep + os.path.join('sys', 'block', device_name, 'dev')
        if not os.path.exists(dev_file):
            return False
        if not os.access(dev_file, os.R_OK):
            log.warn(_("No read access to %r."), dev_file)
            return False

        handler = PbBaseHandler()
        f_content = handler.read_file(dev_file, quiet = True).strip()
        if f_content.startswith('7:'):
            return True

        return False

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(LoopDevice, self).as_dict()
        res['losetup_cmd'] = self.losetup_cmd

        return res


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
