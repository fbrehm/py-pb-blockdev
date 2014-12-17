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

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError

from pb_blockdev.base import BlockDeviceError

from pb_blockdev.translate import translator

from pb_blockdev.multipath import GenericMultipathError
from pb_blockdev.multipath import GenericMultipathHandler

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.1.0'


#==============================================================================
class MultipathSystemError(GenericMultipathError):
    """Base exception class for errors for common system multipath errors"""
    pass


#==============================================================================
class MultipathSystem(GenericMultipathHandler):
    """
    Object for capsulating all common multipath operations stuff.
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            multipathd_command = None,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            initialized = False,
            simulate = False,
            *targs,
            **kwargs
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

        @return: None

        """

        # Initialisation of the parent object
        super(MultipathSystem, self).__init__(
            multipathd_command=multipathd_command,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            simulate=simulate,
            *targs, **kwargs
        )

        if initialized:
            self.initialized = True
            if self.verbose > 3:
                LOG.debug(_("Initialized."))

    #--------------------------------------------------------------------------
    def get_maps(self):
        """
        Retrieves from multipathd all known maps/multipaths.

        @raise MultipathSystemError: on some call errors

        @return: list of dict with fields:
                    * name (e.g. 3600144f00001da8b1774872e11e29a25)
                    * dm_device (e.g. dm-0)
                    * uuid (e.g. 3600144f00001da8b1774872e11e29a25)
        @rtype: list of dict

        """

        if self.verbose > 1:
            LOG.debug(_("Collecting from multipathd all known maps ..."))

        cmd = [self.multipathd_command, 'show', 'maps']
        (ret_code, std_out, std_err) = self.call(
            cmd, quiet=True, sudo=True, simulate=False)

        if ret_code:
            msg = (_("Error %(rc)d executing multipathd: %(msg)s")
                    % {'rc': ret_code, 'msg': std_err})
            raise MultipathSystemError(msg)

        pattern = r'^\s*(\S+)\s+(\S+)\s+(\S+)\s*'
        re_line = re.compile(pattern)

        i = 0
        maps = []

        for line in std_out.splitlines():
            i += 1
            if i == 1:
                continue

            line = line.strip()
            if not line:
                continue

            match = re_line.search(line)
            if match:
                if self.verbose > 3:
                    LOG.debug(_("Match found."))

                mpath = {}
                mpath['name'] = match.group(1)
                mpath['dm_device'] = match.group(2)
                mpath['uuid'] = match.group(3)

                maps.append(mpath)

        return maps


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
