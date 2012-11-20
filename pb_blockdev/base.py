#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a base blockdevice class
"""

# Standard modules
import sys
import os
import logging

from gettext import gettext as _

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

base_sysfs_blockdev_dir = os.sep + os.path.join('sys', 'block')

#==============================================================================
class BlockDeviceError(PbBaseHandlerError):
    """
    Base error class for all exceptions belonging to base block device
    """

    pass

#==============================================================================
class BlockDevice(PbBaseHandler):
    """
    Base block device object.
    """

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
        Initialisation of the base blockdevice object.

        @raise CommandNotFoundError: if some needed commands could not be found.
        @raise BlockDeviceError: on a uncoverable error.

        @param name: name of the blockdevice, like used under /sys/block.
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

        super(BlockDevice, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
                simulate = simulate,
                sudo = False,
                quiet = False,
        )

        self._name = name
        """
        @ivar: name of the blockdevice, like used under /sys/block
        @type: None (if not even discoverd) or str
        """

    #------------------------------------------------------------
    @property
    def name(self):
        """The name of the blockdevice, like used under /sys/block"""
        return getattr(self, '_name', None)

    @name.setter
    def name(self, value):
        if not value:
            msg = _("No new name given.")
            raise BlockDeviceError(msg)
        new_name = str(value).strip()
        if not new_name:
            msg = _("Empty name %r given as name of the blockdevice.") % (
                    value)
            raise BlockDeviceError(msg)
        self._name = new_name

    #------------------------------------------------------------
    @property
    def sysfs_bd_dir(self):
        """The apropriate directory under /sys/block, e.g. /sys/block/sda"""
        if not self.name:
            return None
        return os.path.join(base_sysfs_blockdev_dir, self.name)

    #------------------------------------------------------------
    @property
    def exists(self):
        """Does the blockdevice of the current object exists?"""
        sfs_dir = self.sysfs_bd_dir
        if not sfs_dir:
            return False
        if os.path.exists(sfs_dir):
            return True
        return False

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(BlockDevice, self).as_dict()
        res['sysfs_bd_dir'] = self.sysfs_bd_dir
        res['exists'] = self.exists

        return res


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
