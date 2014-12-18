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

from pb_blockdev.multipath.path import MultipathPathError
from pb_blockdev.multipath.path import MultipathPath

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.4.0'

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
        self, name=None, dm_name=None, auto_discover=False,
            multipathd_command=None, appname=None, verbose=0,
            version=__version__, base_dir=None,
            simulate=False, sudo=False, quiet=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the MultipathDevice object.

        @raise CommandNotFoundError: if the command 'multipathd'
                                     could not be found
        @raise MultipathDeviceError: on a uncoverable error.

        @param name: name of the loop device, e.g. 'dm-1'
        @type name: None (if not even discoverd) or str
        @param dm_name: the devicemapper name
        @type dm_name: str or None
        @param auto_discover: discover paths and properties automatacally
                              after init of this object.
        @type auto_discover: bool
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

        self.paths = []
        """
        @ivar: list of all child paths of this multipath device
        @type: list of MultipathPath
        """

        self._discovered = False
        self._policy = None
        self._prio = None
        self._status = None

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

        if auto_discover:
            self.discover()

        self.initialized = True
        if self.verbose > 3:
            LOG.debug(_("Initialized."))

    # -----------------------------------------------------------
    @property
    def prio(self):
        """The priority of the map."""
        return self._prio

    # -----------------------------------------------------------
    @property
    def policy(self):
        """The multipath policy."""
        return self._policy

    # -----------------------------------------------------------
    @property
    def status(self):
        """The status of the multipath map."""
        return self._status

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

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MultipathDevice, self).as_dict(short=short)
        res['prio'] = self.prio
        res['policy'] = self.policy
        res['status'] = self.status

        res['paths'] = []
        for path in self.paths:
            res['paths'].append(path.as_dict(short=short))

        return res

    # -------------------------------------------------------------------------
    def discover(self):
        """
        Discovering of all properties and paths of this multipath device.
        """

        self.paths = []
        self._policy = None
        self._prio = None
        self._status = None

        if not self.exists:
            return

        LOG.debug(_("Discovering multipath map %r ..."), self.dm_name)

        cmd = [self.multipathd_command, 'show', 'map', self.dm_name, 'topology']
        (ret_code, std_out, std_err) = self.call(
            cmd, quiet=True, sudo=True, simulate=False)

        if ret_code:
            msg = (
                _("Error %(rc)d executing multipathd: %(msg)s") % {
                    'rc': ret_code, 'msg': std_err})
            raise MultipathSystemError(msg)

        """
        Sample output:
        --------------
        3600144f000017d604b3b957d11e39cab dm-45 SCST_FIO,bf82c405e8cfe2de
        size=50G features='0' hwhandler='0' wp=rw
        `-+- policy='round-robin 0' prio=2 status=enabled
          |- 33:0:0:45 sdds 71:160  active ready running
          `- 34:0:0:45 sddt 71:176  active ready running
        """

        pattern_policy_line = r"\spolicy='([^']+)'\s+prio=(-?\d+)"
        pattern_policy_line += r"\s+status=(\S+)"
        re_policy_line = re.compile(pattern_policy_line)

        pattern_path_line = r"\s\d+:\d+:\d+:\d+\s+(\S+)\s+\d+:\d+"
        pattern_path_line += r"\s+(\S+)\s+(\S+)\s+(\S+)"
        re_path_line = re.compile(pattern_path_line)

        policy = None
        prio = None
        status = None

        for line in std_out.split('\n'):

            match = re_policy_line.search(line)
            if match:
                policy = match.group(1)
                prio = int(match.group(2))
                status = match.group(3)
                continue

            match = re_path_line.search(line)
            if match:
                path_name = match.group(1)
                path = MultipathPath(
                    path_name,
                    multipathd_command=self.multipathd_command,
                    appname=self.appname,
                    verbose=self.verbose,
                    base_dir=self.base_dir,
                    simulate=self.simulate,
                    sudo=self.sudo,
                    quiet=self.quiet,
                    initialized=False,
                )
                path.refresh()
                path.initialized = True
                self.paths.append(path)

        self._policy = policy
        self._prio = prio
        self._status = status

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
