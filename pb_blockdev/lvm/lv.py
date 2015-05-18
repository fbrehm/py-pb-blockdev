#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: module for a encapsulation class of a LVM logical volume
"""

# Standard modules
import os
import logging

# Third party modules

# Own modules
from pb_base.common import to_bool

from pb_blockdev.lvm import DEFAULT_LVM_LOCKFILE, DEFAULT_LVM_TIMEOUT

from pb_blockdev.lvm.volume import LvmVolumeError
from pb_blockdev.lvm.volume import LvmVolume

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)



# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
