#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: All modules for handling md devices and commands
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

__version__ = '0.1.0'

MDADM_PATH = os.sep + os.path.join('sbin', 'mdadm')
LOG = logging.getLogger(__name__)


# =============================================================================
class GenericMdError(BlockDeviceError):
    """Base exception class for all md-raid errors"""
    pass


# =============================================================================
class MdadmError(GenericMdError):
    """Exception class for errors on executing mdadm"""
    pass



# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
