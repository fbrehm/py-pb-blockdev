#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for functions for all blockdevice classes
"""

# Standard modules
import sys
import os
import logging
import re

from gettext import gettext as _

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError

from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDevice

from pb_blockdev.loop import LoopDevice

from pb_blockdev.dm import DeviceMapperDevice

from pb_blockdev.scsi import ScsiDevice

__version__ = '0.3.0'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

blockdev_class_list = [
    DeviceMapperDevice,
    LoopDevice,
    ScsiDevice,
    BlockDevice
]

#==============================================================================
def get_blockdev_class(device_name):
    """
    Gives back the appropriate class for the given device name.

    @raise BlockDeviceError: if the given device name is invalid,
                             e.g. has path parts

    @param device_name: the basename of the blockdevice to check, e.g. 'sda'
                        or 'dm-7' or 'loop0' or 'md0'
    @type device_name: str

    @return: the appropriate class tothe given device name.
    @rtype: class

    """

    if not device_name:
        raise BlockDeviceError(_("No device name given."))
    if device_name != os.path.basename(device_name):
        msg  = _("Invalid device name %r given.") % (device_name)
        raise BlockDeviceError(msg)

    for cls in blockdev_class_list:
        if cls.isa(device_name):
            return cls

    return None

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
