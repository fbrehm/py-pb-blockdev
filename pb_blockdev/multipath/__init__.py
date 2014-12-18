#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: All modules for handling multipath devices and commands
"""

# Standard modules
import sys
import os
import re
import logging

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

from pb_blockdev.translate import translator

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.5.1'

MULTIPATHD_PATH = os.sep + os.path.join('sbin', 'multipathd')
LOG = logging.getLogger(__name__)


# =============================================================================
class GenericMultipathError(BlockDeviceError):
    """Base exception class for all multipath errors"""
    pass


# =============================================================================
class ExecMultipathdError(GenericMultipathError):
    """Special exception class for all execution errors on multipathd."""
    pass

# =============================================================================
class MultipathdNotRunningError(ExecMultipathdError):
    """
    Special exception class for the case, that calling 'multipathd' was not
    successful, because the multipathd was not running as daemon.
    """

    # -------------------------------------------------------------------------
    def __init__(self, command, *args, **kwargs):
        """Constructor."""

        self.command = command

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string for error output."""

        msg = to_str_or_bust(_(
            "Could not execute %r, because multipathd is not running as daemon."))
        msg = msg % (self.command)

        return msg


# =============================================================================
class GenericMultipathHandler(PbBaseHandler):
    """
    Base class for all LVM objects
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, multipathd_command=None, appname=None, verbose=0,
            version=__version__, base_dir=None, initialized=False,
            simulate=False, sudo=False, quiet=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the generic multipath handler object.

        @raise CommandNotFoundError: if the command 'multipathd'
                                     could not be found
        @raise GenericMultipathError: on a uncoverable error.

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

        # /sbin/multipathd
        self._multipathd_command = MULTIPATHD_PATH
        """
        @ivar: the 'multipathd' command in operating system
        @type: str
        """

        # Initialisation of the parent object
        super(GenericMultipathHandler, self).__init__(
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            initialized=False,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )

        failed_commands = []

        # Check of the multipathd command
        if multipathd_command:
            self._multipathd_command = multipathd_command
        if not os.path.exists(self._multipathd_command):
            failed_commands.append('multipathd')

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        if initialized:
            self.initialized = True
            if self.verbose > 3:
                LOG.debug(_("Initialized."))

    # -------------------------------------------------------------------------
    @property
    def multipathd_command(self):
        'The "multipathd" command in operating system'
        return self._multipathd_command

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(GenericMultipathHandler, self).as_dict(short=short)
        res['multipathd_command'] = self.multipathd_command

        return res

    # -------------------------------------------------------------------------
    def exec_multipathd(self, cmd_params, quiet=True, simulate=None):
        """
        Execute multipathd with the given parameters.

        @raise MultipathdNotRunningError: if the command fails, because
                                          the multipathd is not running
                                          as daemon currently

        @param cmd_params: all parameters for calling multipathd
        @type cmd_params: list of str
        @param quiet: quiet execution of the command
        @type quiet: bool
        @param simulate: coerced simulation of the command
        @type simulate: bool

        """

        cmd = [self.multipathd_command]
        cmd_str = self.multipathd_command
        if isinstance(cmd_params, list):
            for p in cmd_params:
                cmd.append(p)
                cmd_str += " " + ("%r" % (str(p)))
        else:
            cmd.append(str(cmd_params))
            cmd_str += " " + ("%r" % (str(cmd_params)))

        do_sudo = False
        if os.geteuid():
            do_sudo = True
        if do_sudo:
            LOG.debug(
                to_str_or_bust(_("Executing as root:")) + " %s",
                cmd_str)
        else:
            LOG.debug(to_str_or_bust(_("Executing:")) + " %s", cmd_str)

        (ret_code, std_out, std_err) = self.call(
            cmd, quiet=True, sudo=do_sudo, simulate=simulate)

        if ret_code:
            # ux_socket_connect: No such file or directory
            p_ux_socket_connect = r'^\s*ux_socket_connect:\s+No\s+such'
            p_ux_socket_connect += r'\s+file\s+or\s+directory'
            re_ux_socket_connect = re.compile(p_ux_socket_connect, re.IGNORECASE)
            if ret_code == 1 and re_ux_socket_connect.search(std_err):
                raise MultipathdNotRunningError(cmd_str)
            msg = to_str_or_bust(
                _("Error %(rc)d executing \"%(cmd)s\": %(msg)s")) % {
                    'rc': ret_code, 'cmd': cmd_str, 'msg': std_err}
            raise ExecMultipathdError(msg)
        return (ret_code, std_out, std_err)

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
