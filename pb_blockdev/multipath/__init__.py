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

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.3.0'

MULTIPATHD_PATH = os.sep + os.path.join('sbin', 'multipathd')


#==============================================================================
class GenericMultipathError(BlockDeviceError):
    """Base exception class for all multipath errors"""
    pass


#==============================================================================
class MultipathSystemError(GenericMultipathError):
    """Base exception class for errors for common system multipath errors"""
    pass


#==============================================================================
class GenericMultipathHandler(PbBaseHandler):
    """
    Base class for all LVM objects
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
            *targs, **kwargs
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

    #--------------------------------------------------------------------------
    @property
    def multipathd_command(self):
        'The "multipathd" command in operating system'
        return self._multipathd_command

    #--------------------------------------------------------------------------
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


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
