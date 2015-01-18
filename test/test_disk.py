#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on disk objects
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

from pb_blockdev.disk import Disk

log = logging.getLogger('test_disk')


# =============================================================================
class TestDisk(BlockdevTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a Disk object.")

        disk = Disk(
            name='sda',
            auto_discover=False,
            appname=self.appname,
            verbose=self.verbose,
        )
        if self.verbose > 2:
            log.debug("Disk object:\n%s", disk)

        self.assertIsInstance(disk, Disk)
        del disk

    # -------------------------------------------------------------------------
    def test_empty_object(self):

        log.info("Testing init of a Disk object without a name.")

        disk = Disk(
            name=None,
            auto_discover=False,
            appname=self.appname,
            verbose=self.verbose,
        )
        if self.verbose > 2:
            log.debug("Disk object:\n%s", disk)

        self.assertIsInstance(disk, Disk)
        del disk

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.geteuid() == 0, "Only root may perform disk operations.")
    def test_discovery_disk(self):

        log.info("Testing discovery of a partitioned disk.")

        sd_dir_pattern = os.sep + os.path.join('sys', 'block', 'sd*')
        if self.verbose > 2:
            log.debug(
                "searching for blockdevices with pattern: %r",
                sd_dir_pattern)
        sd_dirs = glob.glob(sd_dir_pattern)

        if not sd_dirs:
            self.skipTest("No appropriate block devices found.")
            return

        bd_name = os.path.basename(sd_dirs[0])
        log.debug("Using %r for discovering partitions ...", bd_name)

        disk = Disk(
            name=bd_name,
            auto_discover=True,
            appname=self.appname,
            verbose=self.verbose,
        )
        if self.verbose > 2:
            log.debug("Disk object:\n%s", disk)

        self.assertIsInstance(disk, Disk)
        del disk

# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestDisk('test_object', verbose))
    suite.addTest(TestDisk('test_empty_object', verbose))
    suite.addTest(TestDisk('test_discovery_disk', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
