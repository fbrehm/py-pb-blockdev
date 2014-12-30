#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: All modules for handling mdadm actions independent
          of a particular MD device
"""

# Standard modules
import sys
import os
import re
import logging
import socket

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust
from pb_base.common import to_str_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_base.errors import CouldntOccupyLockfileError
from pb_base.handler.lock import PbLock
from pb_base.handler.lock import PbLockHandler
from pb_base.handler.lock import LockHandlerError

from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BASE_SYSFS_BLOCKDEV_DIR

from pb_blockdev.md import uuid_to_md, uuid_from_md
from pb_blockdev.md import GenericMdError, MdadmError
from pb_blockdev.md import DEFAULT_MDADM_LOCKFILE
from pb_blockdev.md import GenericMdHandler

from pb_blockdev.translate import translator

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)

DEFAULT_MD_FORMAT = '1.2'
DEFAULT_HOMEHOST = 'virtualhost'
DEFAULT_ARRAY_NAME = '0'

VALID_MD_FORMATS = ('0', '0.90', '1', '1.0', '1.1', '1.2', 'default')
"""
A list of all available RAID metadata (superblock) formats,
that can be used.
"""

VALID_MD_LEVELS = (
        'linear', 'raid0', '0', 'stripe',
        'raid1', '1', 'mirror',
        'raid4', '4',
        'raid5', '5',
        'raid6', '6',
        'raid10', '10',
)
"""
A list of all available RAID levels, that canbe used to create a new MD device.
Following md levels are possible for mdadm, but not supported in this module::
 * multipath
 * mp
 * faulty
 * container
"""

#==============================================================================
class MdAdm(GenericMdHandler):
    """
    Class for a MdAdm handler Object for all actions around mdadm
    independent of a particular MD device
    """

    #--------------------------------------------------------------------------
    def __init__(
        self,
            default_md_format=DEFAULT_MD_FORMAT,
            default_homehost=DEFAULT_HOMEHOST,
            default_array_name=DEFAULT_ARRAY_NAME,
            mdadm_command=None, mdadm_lockfile=DEFAULT_MDADM_LOCKFILE,
            appname=None, verbose=0, version=__version__, base_dir=None,
            initialized=False, simulate=False, sudo=False, quiet=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the mdadm handler object.

        @raise CommandNotFoundError: if the command 'mdadm'
                                     could not be found
        @raise MdadmError: on a uncoverable error.

        @param default_md_format: default format of the metadata superblock,
                                  that is used for creating the new
                                  metadevice, if None is given
        @type default_md_format: str
        @param default_homehost: homehost option used for creating a special
                                 degraded RAID device
        @type default_homehost: str
        @param default_array_name: default name of the array on some circumstances
                                   (if needed)
        @type default_array_name: str
        @param mdadm_command: path to executable mdadm command
        @type mdadm_command: str
        @param mdadm_lockfile: the global lockfile used for mdadm execution
        @type mdadm_lockfile: str

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

        self._default_md_format = default_md_format
        """
        @ivar: format of the metadata superblock, that is used for
               creating the new metadevice, if None is given
        @type: str
        """

        self._default_homehost = default_homehost
        """
        @ivar: homehost option used for creating our special degraded RAID device
        @type: str
        """

        self._default_array_name = default_array_name
        """
        @ivar: default name of the array on some circumstances (if needed)
        @type: str
        """

        # Initialisation of the parent object
        super(MdAdm, self).__init__(
            mdadm_command=mdadm_command,
            mdadm_lockfile=mdadm_lockfile,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            initialized=False,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )

        if not self.default_md_format:
            self._default_md_format = DEFAULT_MD_FORMAT
        if not self.default_homehost:
            self._default_homehost = DEFAULT_HOMEHOST
        if not self.default_array_name:
            self._default_array_name = DEFAULT_ARRAY_NAME

        self.initialized = True

    #------------------------------------------------------------
    @property
    def default_md_format(self):
        """The format of the metadata superblock, that is used for creating."""
        return self._default_md_format

    #------------------------------------------------------------
    @property
    def default_homehost(self):
        """The homehost option used for creating our special degraded RAID device."""
        return self._default_homehost

    #------------------------------------------------------------
    @property
    def default_array_name(self):
        """The default name of the array on some circumstances (if needed)."""
        return self._default_array_name

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MdAdm, self).as_dict(short=short)
        res['default_md_format'] = self.default_md_format
        res['default_homehost'] = self.default_homehost
        res['default_array_name'] = self.default_array_name

        return res

    #--------------------------------------------------------------------------
    def _get_new_md_device_id(self, release_lock=False):
        """
        Retrieve a new, unused MD device id. It sets first a lock for this
        action.

        @raise MdadmError: if the lock could not be created.

        @param release_lock: release the global lock after finding
                             the new device Id
        @type release_lock: bool

        @return: the new md device id
        @rtype: int

        """

        md_id = None

        if not self.global_lock:
            self.lock_global()

        i = 0
        max_id = 10000
        while md_id is None:
            dev_dir = os.path.join(BASE_SYSFS_BLOCKDEV_DIR, ('md%d' % (i)))
            if not os.path.exists(dev_name):
                md_id = i
                break
            i += 1
            if i >= max_id:
                msg = to_str_or_bust(_("Maximum MD ID of %d reached.")) % (max_id)
                self.global_lock = None
                raise MdadmError(msg)

        if release_lock:
            self.global_lock = None

        return md_id



# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
