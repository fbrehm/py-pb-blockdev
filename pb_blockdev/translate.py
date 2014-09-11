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

log = logging.getLogger(__name__)

basedir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
locale_dir = os.path.join(basedir, 'po')
if not os.path.isdir(locale_dir):
    locale_dir = None

mo_file = gettext.find('py_pb_blockdev', locale_dir)

translator = gettext.translation('py_pb_blockdev', locale_dir, fallback = True)
"""
The main gettext-translator object, which can be imported
from other modules.
"""

_ = translator.lgettext
__ = translator.lngettext

#==============================================================================

if __name__ == "__main__":

    print _("Basedir: %r") % (basedir)
    print _("Found .mo-file: %r") % (mo_file)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
