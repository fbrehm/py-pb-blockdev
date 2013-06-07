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

import unittest2
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
from pb_blockdev.base import format_bytes, size_to_sectors

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
            self.skipTest("Directory %r not found." % (bd_dir))

        dirs = glob.glob(os.path.join(bd_dir, '*'))
        devs = map(lambda x: os.path.basename(x), dirs)
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]

        if self.verbose > 1:
            log.debug("Got a random blockdevice name %r.", devname)

        return devname

    #--------------------------------------------------------------------------
    def test_format_bytes(self):

        log.info("Testing format_bytes ...")

        units = (None, 'bla', 'KB')
        for unit in units:
            log.debug("Testing invalid unit %r ...", unit)
            with self.assertRaises(SyntaxError) as cm:
                result = format_bytes(1024, unit)
                log.debug("Got a result %r.", result)
            e = cm.exception
            log.debug("%s raised on format_bytes() with unit %r: %s",
                    'SyntaxError', unit, e)

        values = (
            (1024, 'B', 1024),
            (1024, 'KiB', 1),
            (1000, 'kB',  1),
            (1024, 'kB',  1),
            ((1024 * 1024), 'KiB', 1024),
            ((1024 * 1024), 'kB', 1048),
            ((1000 * 1000), 'kB', 1000),
            ((1024l * 1024l * 1024l * 1024l * 1024l), 'GiB', (1024l * 1024l)),
        )

        for tpl in values:
            val = tpl[0]
            unit = tpl[1]
            exp_result = tpl[2]

            log.debug("Converting %r into %r, expected result: %r.",
                    val, unit, exp_result)

            result = format_bytes(val, unit)
            log.debug("Got converted result: %r", result)
            self.assertEqual(result, exp_result)

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

    suite = unittest2.TestSuite()

    suite.addTest(TestBlockDevice('test_format_bytes', verbose))
    suite.addTest(TestBlockDevice('test_object', verbose))
    suite.addTest(TestBlockDevice('test_existing', verbose))
    suite.addTest(TestBlockDevice('test_statistics', verbose))

    runner = unittest2.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
