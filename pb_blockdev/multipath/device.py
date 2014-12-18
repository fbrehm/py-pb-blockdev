#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Encapsulation module for a multipath device
"""

# Standard modules
import sys
import os
import re
import logging

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_blockdev.base import BlockDeviceError

from pb_blockdev.translate import translator

from pb_blockdev.multipath import GenericMultipathError
from pb_blockdev.multipath import GenericMultipathHandler

from pb_blockdev.dm import DmDeviceError
from pb_blockdev.dm import DeviceMapperDevice

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.2.0'

LOG = logging.getLogger(__name__)


# =============================================================================
class MultipathDeviceError(DmDeviceError, GenericMultipathError):
    """Base exception class for all errors with multipath devices."""
    pass


# =============================================================================
class MultipathDevice(DeviceMapperDevice, GenericMultipathHandler):
    """Encapsulation class for a multipath device."""

    # -------------------------------------------------------------------------
    def __init__(
        self, name=None, dm_name=None, multipathd_command=None,
            appname=None, verbose=0, version=__version__, base_dir=None,
            simulate=False, sudo=False, quiet=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the MultipathDevice object.

        @raise CommandNotFoundError: if the command 'multipathd'
                                     could not be found
        @raise MultipathDeviceError: on a uncoverable error.

        @param multipathd_command: path to executable multipathd command
        @type multipathd_command: str
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
        @param sudo: should the command executed by sudo by default
        @type sudo: bool
        @param quiet: don't display ouput of action after calling
        @type quiet: bool

        @return: None

        """
        # Initialisation of the parent object
        super(MultipathDevice, self).__init__(
            name=name,
            dm_name=dm_name,
            multipathd_command=multipathd_command,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
            initialized=False,
            *targs, **kwargs
        )

        self.initialized = True
        if self.verbose > 3:
            LOG.debug(_("Initialized."))

    # -------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable multipath device.

        @raise MultipathDeviceError: if the given device name is invalid,

        @param device_name: the basename of the multipath device to check, e.g. 'dm-0'
        @type device_name: str

        @return: the given device name is usable as a multipath device name and exists.
        @rtype: bool

        """

        if not device_name:
            raise MultipathDeviceError(_("No device name given."))
        if device_name != os.path.basename(device_name):
            msg = _("Invalid device name %r given.") % (device_name)
            raise MultipathDeviceError(msg)

        bd_dir = os.sep + os.path.join('sys', 'block', device_name)
        if not os.path.exists(bd_dir):
            return False

        dm_dir = os.path.join(bd_dir, 'dm')
        if not os.path.exists(dm_dir):
            return False
        if not os.path.isdir(dm_dir):
            return False

        uuid_file = os.path.join(dm_dir, 'uuid')
        if not os.path.exists(uuid_file):
            return False
        if not os.access(uuid_file, os.R_OK):
            log.warn(_("No read access to %r."), uuid_file)
            return False

        handler = PbBaseHandler()
        f_content = handler.read_file(uuid_file, quiet=True).strip()
        if f_content.startswith('mpath-'):
            return True

        return False


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4