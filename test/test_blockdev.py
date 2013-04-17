#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on base blockdevice object
'''

import unittest
import os
import sys
import random
import glob
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import BlockdevTestcase, get_arg_verbose, init_root_logger

from pb_base.common import pp

import pb_blockdev.base
from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDeviceStatistic
from pb_blockdev.base import BlockDevice

log = logging.getLogger(__name__)

#==============================================================================

class TestBlockDevice(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        self.appname = 'test_blockdev'

    #--------------------------------------------------------------------------
    def get_random_blockdev_name(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, '*'))
        devs = map(lambda x: os.path.basename(x), dirs)
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]

        if self.verbose > 1:
            log.debug("Got a random blockdevice name %r.", devname)

        return devname

    #--------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a BlockDevice object.")

        obj = BlockDevice(
                name = 'sda',
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("BlockDevice object:\n%s", obj)

        self.assertIsInstance(obj, BlockDevice)
        del obj

    #--------------------------------------------------------------------------
    def test_existing(self):

        devname = self.get_random_blockdev_name()
        blockdev = None

        log.info("Testing of a BlockDevice object of the existing block device %r.",
                devname)

        blockdev = BlockDevice(
                name = devname,
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("BlockDevice object:\n%s", blockdev)
        self.assertIsInstance(blockdev, BlockDevice)
        self.assertEqual(blockdev.exists, True)

    #--------------------------------------------------------------------------
    def test_statistics(self):

        devname = self.get_random_blockdev_name()
        blockdev = None

        log.info("Testing of getting statistics of the existing block device %r.",
                devname)

        blockdev = BlockDevice(
                name = devname,
                appname = self.appname,
                verbose = self.verbose,
        )
        self.assertIsInstance(blockdev, BlockDevice)

        stats = blockdev.get_statistics()
        self.assertIsInstance(stats, BlockDeviceStatistic)
        if self.verbose > 1:
            log.debug("Blockdevice statistics of %r:\n%s",
                    blockdev.device, stats)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestBlockDevice('test_object', verbose))
    suite.addTest(TestBlockDevice('test_existing', verbose))
    suite.addTest(TestBlockDevice('test_statistics', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
