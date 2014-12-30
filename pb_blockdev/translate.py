#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for i18n.
          It provides translation object, usable from all other
          modules in this package.
"""

# Standard modules
import sys
import os
import logging
import gettext

# Own modules
from pb_base.common import to_str_or_bust

LOG = logging.getLogger(__name__)

basedir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
locale_dir = os.path.join(basedir, 'po')
if not os.path.isdir(locale_dir):
    locale_dir = None

mo_file = gettext.find('py_pb_blockdev', locale_dir)

translator = gettext.translation('py_pb_blockdev', locale_dir, fallback=True)
"""
The main gettext-translator object, which can be imported
from other modules.
"""

# =============================================================================
def pb_gettext(message):
    if sys.version_info[0] > 2:
        return to_str_or_bust(translator.gettext(message))
    else:
        return to_str_or_bust(translator.lgettext(message))


# =============================================================================
def pb_ngettext(singular, plural, n):
    if sys.version_info[0] > 2:
        return to_str_or_bust(translator.ngettext(singular, plural, n))
    else:
        return to_str_or_bust(translator.lngettext(singular, plural, n))


# =============================================================================
# Wrapper functions
_ = pb_gettext
__ = pb_ngettext



# =============================================================================
if __name__ == "__main__":

    print(_("Basedir: %r") % (basedir))
    print(_("Found .mo-file: %r") % (mo_file))

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
