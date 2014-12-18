#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for a encaplusation class for a multipath path
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

from pb_blockdev.base import BlockDeviceError

from pb_blockdev.translate import translator

from pb_blockdev.scsi import ScsiDevice

from pb_blockdev.multipath import GenericMultipathError
from pb_blockdev.multipath import GenericMultipathHandler

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)


# =============================================================================
class MultipathPathError(GenericMultipathError):
    """Base exception class for errors in the MultipathPath class."""
    pass


# =============================================================================
class MultipathPath(GenericMultipathHandler):
    """
    Object for capsulating a multipath path.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, name, prio=None, dm_state=None, check_state=None,
            device_state=None, max_wait_for_delete=5, multipathd_command=None,
            appname=None, verbose=0, version=__version__, base_dir=None,
            initialized=None, simulate=False, sudo=False, quiet=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the multipath path object.

        @raise CommandNotFoundError: if the command 'multipathd'
                                     could not be found
        @raise MultipathPathError: on a uncoverable error.

        @param name: the name of the underlaying SCSI device.
        @type name: str
        @param prio: the numeric priority
        @type prio: int
        @param dm_state: the Device-Mapper state
        @type dm_state: str
        @param check_state: the state of the last check of the device
                            by multipathd
        @type check_state: str
        @param device_state: the state of the underlaying SCSI device
        @type device_state: str
        @param multipathd_command: path to executable multipathd command
        @type multipathd_command: str

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

        self.device = None
        """
        @ivar: The underlaying SCSI device object
        @type: ScsiDevice
        """

        self._prio = None
        self._dm_state = None
        self._check_state = None
        self._device_state = None
        self._max_wait_for_delete = 5.0

        # Initialisation of the parent object
        super(MultipathPath, self).__init__(
            multipathd_command=multipathd_command,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
            initialized=False,
        )

        if prio is not None:
            self._prio = int(prio)

        if dm_state is not None:
            self._dm_state = str(dm_state).lower().strip()

        if check_state is not None:
            self._check_state = str(check_state).lower().strip()

        if device_state is not None:
            self._device_state = str(device_state).lower().strip()

        self.device = ScsiDevice(
            name=name,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )
        self.device.initialized = False

        if initiallized is None or initialized:
            self.initialized = True
            if self.verbose > 3:
                LOG.debug(_("Initialized."))

    # -----------------------------------------------------------
    @property
    def name(self):
        """The name of the blockdevice, like used under /sys/block"""
        if not self.device:
            return None
        return self.device.name

    # -----------------------------------------------------------
    @property
    def prio(self):
        """The priority of the path."""
        return self._prio

    # -----------------------------------------------------------
    @property
    def dm_state(self):
        """The state of the path inside the devicemapper device (?)"""
        return self._dm_state

    @dm_state.setter
    def dm_state(self, value):
        if not value:
            self._dm_state = None
            return
        v = str(value).lower().strip()
        if not v:
            self._dm_state = None
            return
        self._dm_state = v

    # -----------------------------------------------------------
    @property
    def check_state(self):
        """The state of the last check of the device by multipathd."""
        return self._check_state

    @check_state.setter
    def check_state(self, value):
        if not value:
            self._check_state = None
            return
        v = str(value).lower().strip()
        if not v:
            self._check_state = None
            return
        self._check_state = v

    # -----------------------------------------------------------
    @property
    def device_state(self):
        """The state of the underlaying SCSI device."""
        if self.device and self.device.exists:
            return self.device.state
        return self._device_state

    @device_state.setter
    def device_state(self, value):
        if not value:
            self._device_state = None
            return
        v = str(value).lower().strip()
        if not v:
            self._device_state = None
            return
        self._device_state = v

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MultipathPath, self).as_dict(short=short)
        res['name'] = self.name
        res['prio'] = self.prio
        res['dm_state'] = self.dm_state
        res['check_state'] = self.check_state
        res['device_state'] = self.device_state

        return res

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
