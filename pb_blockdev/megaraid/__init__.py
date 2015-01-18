#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for a collection of MegaRaid error classes
"""

# Standard modules
import logging

# Third party modules

# Own modules
from pb_base.object import PbBaseObjectError

from pb_base.app import PbApplicationError

from pb_base.handler import PbBaseHandlerError


__version__ = '0.2.2'

log = logging.getLogger(__name__)


# =============================================================================
class MegaraidError(PbBaseObjectError):
    """Base error class for all stuff belonging to MegaRaid."""
    pass


# =============================================================================
class MegaraidHandlerError(PbBaseHandlerError, MegaraidError):
    """Base error class for MegaraidHandler methods."""
    pass


# =============================================================================
class MegaraidEnclosureError(MegaraidError):
    """Base error class for all stuff belonging to MegaraidEnclosure."""
    pass


# =============================================================================
class MegaraidPdError(MegaraidError):
    """Base error class for all stuff belonging to MegaraidPd."""
    pass


# =============================================================================
class MegaraidPdsError(PbApplicationError, MegaraidError):
    """Base error class for all exceptions happened during
    execution of 'megaraid-pds'"""
    pass


# =============================================================================
class MegaraidLdError(MegaraidError):
    """Base error class for all stuff belonging to MegaraidLd."""
    pass


# =============================================================================
class MegaraidLdsError(PbApplicationError, MegaraidError):
    """Base error class for all exceptions happened during
    execution of 'megaraid-lds'"""
    pass


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
