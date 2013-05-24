#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2013 by Profitbricks GmbH
@license: GPL3
@summary: Module for a class for partitioned Disk
"""

# Standard modules
import sys
import os
import logging
import re
import glob
import time

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

from pb_blockdev.translate import translator

from pb_parted import PartedHandlerError
from pb_parted import PartedHandler

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.2.0'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

VALID_DISK_UNIT_MODES = ('BYT', 'CHS', 'CYL')


#==============================================================================
class DiskError(BlockDeviceError):
    """
    Base error class for all exceptions belonging to the disk module
    """

    pass

#==============================================================================
class Disk(BlockDevice):
    """
    A class for encapsulating a partitioned disk (HD or such similar).
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            name,
            auto_discover = False,
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
        Initialisation of the partitioned disk object.

        @raise DiskError: on a uncoverable error.

        @param name: name of the disk, e.g. 'sda'
        @type name: None (if not even discoverd) or str
        @param auto_discover: automatic discovering of partitions
                              after initialization
        @type auto_discover: bool
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

        super(Disk, self).__init__(
                name = name,
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                simulate = simulate,
                initialized = False,
        )
        self.initialized = False

        self._disk_discovered = False
        """
        @ivar: flag, whether the disk was discovered via 'parted'
        @type: bool
        """

        self._auto_discover = bool(auto_discover)
        """
        @ivar: automatic discovering of partitions after initialization
        @type: bool
        """

        self.partitions = []
        """
        @ivar: a list with all partition objects
        @type: list of Partition objects
        """

        self.parted = PartedHandler(
                appname = self.appname,
                verbose = self.verbose,
                base_dir = self.base_dir,
                use_stderr = self.use_stderr,
                simulate = self.simulate,
        )
        """
        @ivar: a handler object to execute 'parted'
        @type: PartedHandler
        """

        self.initialized = True

    #------------------------------------------------------------
    @property
    def disk_discovered(self):
        """A flag, whether the disk was discovered via 'parted'."""
        return self._disk_discovered

    #------------------------------------------------------------
    @property
    def auto_discover(self):
        """Execute automatic discovering of partitions after initialization."""
        return self._auto_discover

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(Disk, self).as_dict(short = short)
        res['disk_discovered'] = self.disk_discovered
        res['auto_discover'] = self.auto_discover
        res['partitions'] = []
        for partition in self.partitions:
            res['partitions'].append(partition.as_dict(short))

        return res


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
