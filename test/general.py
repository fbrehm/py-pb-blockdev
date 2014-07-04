#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010-2013 by Profitbricks GmbH
@license: GPL3
@summary: general used functions an objects used for unit tests on
          the blockdevice handler package
"""

import unittest2
import os
import sys
import logging
import argparse

# Own modules

from pb_logging.colored import ColoredFormatter

#==============================================================================

log = logging.getLogger(__name__)

#==============================================================================
def get_arg_verbose():

    arg_parser = argparse.ArgumentParser()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action = "count",
            dest = 'verbose', help = 'Increase the verbosity level')
    args = arg_parser.parse_args()

    return args.verbose

#==============================================================================
def init_root_logger(verbose = 0):

    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)
    if verbose:
         root_log.setLevel(logging.DEBUG)

    appname = os.path.basename(sys.argv[0])
    format_str = appname + ': '
    if verbose:
        if verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    formatter = ColoredFormatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)

#==============================================================================
class BlockdevTestcase(unittest2.TestCase):

    #--------------------------------------------------------------------------
    def __init__(self, methodName = 'runTest', verbose = 0):

        self._verbose = int(verbose)

        super(BlockdevTestcase, self).__init__(methodName)

    #--------------------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    #--------------------------------------------------------------------------
    def setUp(self):

        pass

    #--------------------------------------------------------------------------
    def tearDown(self):

        pass

#==============================================================================

if __name__ == '__main__':

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
