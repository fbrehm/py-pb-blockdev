#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: module for base class of volume based LVM objects
"""

# Standard modules
import os
import logging

# Third party modules

# Own modules
from pb_base.common import to_bool

from pb_blockdev.lvm import GenericLvmError
from pb_blockdev.lvm import GenericLvmHandler
from pb_blockdev.lvm import DEFAULT_LVM_LOCKFILE, DEFAULT_LVM_TIMEOUT

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)


# =============================================================================
class LvmVolumeError(GenericLvmError):
    '''
    Base error class
    '''
    pass


# =============================================================================
class LvmVolume(GenericLvmHandler):
    """
    Base class for PhysicalVolume, VolumeGroup and LogicalVolume.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, name, path, vgname, attr, uuid, used=False, discovered=None,
            lvm_command=None, lvm_lockfile=DEFAULT_LVM_LOCKFILE, lvm_timeout=DEFAULT_LVM_TIMEOUT,
            appname=None, verbose=0, version=__version__, base_dir=None,
            use_stderr=False, simulate=False, sudo=False, quiet=False, ):
        """
        Initialisation of the LVM volume object.

        @raise CommandNotFoundError: if the needed commands could not be found.
        @raise LvmVolumeError: on a uncoverable error.

        @param name: name of the LVM volume
        @type name: str
        @param path: path to the LVM volume device
        @type path: str
        @param vgname: the name of the volume group,
                       where the volume belongs to
        @type vgname: str
        @param attr: attributes of this volume
        @type attr: str
        @param uuid: the uuid of this volume
        @type uuid: uuid
        @param used: flag, showing, that this LVM volume is used
        @type used: bool
        @param discovered: is this object already discovered?
                           (True, False or None)
        @type discovered: bool or None

        @param lvm_command: path to executable 'lvm' command
        @type lvm_command: str
        @param lvm_lockfile: the global lockfile used for lvm execution
        @type lvm_lockfile: str
        @param lvm_timeout: timeout for execution the lvm command
        @type lvm_timeout: int or None

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
        super(LvmVolume, self).__init__(
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
