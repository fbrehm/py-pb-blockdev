#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on getting the correc
          blockdevice class
'''

import os
import sys
import glob
import logging

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

from general import BlockdevTestcase, get_arg_verbose, init_root_logger

log = logging.getLogger("test_get_blockdev_class")


# =============================================================================
class TestGetBlockDevClass(BlockdevTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def test_import(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing pb_blockdev.devices ...")
        import pb_blockdev.devices                          # noqa

        log.debug("Importing get_blockdev_class from  pb_blockdev.devices ...")
        from pb_blockdev.devices import get_blockdev_class  # noqa

    # -------------------------------------------------------------------------
    def test_get(self):

        log.info("Testing determining the correct block device name.")

        from pb_blockdev.devices import get_blockdev_class
        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, '*'))
        devs = map(lambda x: os.path.basename(x), dirs)
        print ""
        for dev in sorted(devs):
            cls = get_blockdev_class(dev)
            name = 'None'
            if cls:
                name = cls.__name__
            print "%-8r\t-> %s" % (dev, name)

# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestGetBlockDevClass('test_import', verbose))
    suite.addTest(TestGetBlockDevClass('test_get', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
