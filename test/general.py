#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: general used functions an objects used for unit tests on
          the blockdevice handler package
"""

import os
import sys
import logging
import argparse
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Own modules

from pb_logging.colored import ColoredFormatter

from pb_base.common import to_utf8_or_bust

# =============================================================================

log = logging.getLogger(__name__)


# =============================================================================
def get_arg_verbose():

    arg_parser = argparse.ArgumentParser()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-v", "--verbose", action="count",
        dest='verbose', help='Increase the verbosity level')
    args = arg_parser.parse_args()

    return args.verbose


# =============================================================================
def init_root_logger(verbose=0):

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


# =============================================================================
class BlockdevTestcase(unittest.TestCase):

    # -------------------------------------------------------------------------
    def __init__(self, methodName='runTest', verbose=0):

        self._verbose = int(verbose)

        appname = os.path.basename(sys.argv[0]).replace('.py', '')
        self._appname = appname

        super(BlockdevTestcase, self).__init__(methodName)

    # -------------------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    # -------------------------------------------------------------------------
    @property
    def appname(self):
        """The name of the current running application."""
        return self._appname

    # -------------------------------------------------------------------------
    def setUp(self):

        pass

    # -------------------------------------------------------------------------
    def tearDown(self):

        pass

    # -------------------------------------------------------------------------
    def create_tempfile(self, size=20):
        """
        Creating a temporary file of the given size. After creation the given
        count of 1 MiBytes binary zeroes are written in the file.

        @param size: the count of 1 MiBytes binary zeroes to write into this file
        @type: int

        @return: the filename of the created temporary file.
        @rtype: str

        """

        fd = None
        filename = None
        (fd, filename) = tempfile.mkstemp(suffix='.img', prefix='tmp_')
        log.debug("Created temporary file %r.", filename)
        zeroes = to_utf8_or_bust(chr(0) * 1024 * 1024)
        log.debug("Writing %d MiB binary zeroes into %r ...", size, filename)

        all_ok = False
        try:
            i = 0
            while i < size:
                os.write(fd, zeroes)
                i += 1
            all_ok = True
        finally:
            os.close(fd)
            if not all_ok:
                os.remove(filename)

        if all_ok:
            return filename
        return None


# =============================================================================

if __name__ == '__main__':

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
