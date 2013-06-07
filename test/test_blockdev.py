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
                    e.__class__.__name__, unit, e)

        for bytes_ in (None, 'bla'):
            log.debug("Testing invalid Bytes value %r ...", bytes_)

            with self.assertRaises(Exception) as cm:
                result = format_bytes(bytes_, 'B')
                log.debug("Got a result %r.", result)
            e = cm.exception
            log.debug("%s raised on format_bytes() with value %r: %s",
                    e.__class__.__name__, bytes_, e)

            with self.assertRaises(Exception) as cm:
                result = format_bytes(bytes_, 'B', True)
                log.debug("Got a result %r.", result)
            e = cm.exception
            log.debug("%s raised on format_bytes() with value %r: %s",
                    e.__class__.__name__, bytes_, e)

        values = (
            (1024, 'B', 1024, 1024.0),
            (1024, 'KiB', 1, 1.0),
            (1000, 'kB',  1, 1.0),
            (1024, 'kB',  1, 1.024),
            ((1024 * 1024), 'KiB', 1024, 1024.0),
            ((1024 * 1024), 'kB', 1048, 1048.576),
            ((1000 * 1000), 'kB', 1000, 1000.0),
            ((1024l * 1024l * 1024l * 1024l * 1024l), 'GiB', (1024l * 1024l), float(1024l * 1024l)),
        )

        for tpl in values:

            val = tpl[0]
            unit = tpl[1]
            exp_result = tpl[2]
            exp_result_f = tpl[3]

            log.debug("Converting %r into %r, expected result: %r.",
                    val, unit, exp_result)
            result = format_bytes(val, unit)
            log.debug("Got converted result: %r", result)
            self.assertEqual(result, exp_result)

            log.debug("Converting %r into %r as float, expected result: %r.",
                    val, unit, exp_result_f)
            result_f = format_bytes(val, unit, True)
            log.debug("Got converted float result: %r", result_f)
            self.assertEqual(result_f, exp_result_f)

    #--------------------------------------------------------------------------
    def test_size_to_sectors(self):

        log.info("Testing size_to_sectors() ...")

        units = (None, 'bla', 'KB')
        for unit in units:
            log.debug("Testing invalid unit %r ...", unit)
            with self.assertRaises(SyntaxError) as cm:
                result = size_to_sectors(1024, unit)
                log.debug("Got a result %r.", result)
            e = cm.exception
            log.debug("%s raised on size_to_sectors() with unit %r: %s",
                    e.__class__.__name__, unit, e)

        values = (
            (1024, 'B',   None,    2),
            (1024, 'B',    512,    2),
            (1024, 'B',   1024,    1),
            (   1, 'MiB', None, 2048),
            (   2, 'MiB', 4096,  512),
            (   1, 'MB',  None, 1953),
            (  2l, 'GiB', None,  long(4096 * 1024)),
        )

        for tpl in values:

            val = tpl[0]
            unit = tpl[1]
            sectorsize = tpl[2]
            exp_result = tpl[3]

            log.debug("Converting %d %s into sectors of %r Bytes, expected result: %r.",
                    val, unit, sectorsize, exp_result)

            result = None
            if sectorsize is None:
                result = size_to_sectors(val, unit)
            else:
                result = size_to_sectors(val, unit, sectorsize)
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
    suite.addTest(TestBlockDevice('test_size_to_sectors', verbose))
    suite.addTest(TestBlockDevice('test_object', verbose))
    suite.addTest(TestBlockDevice('test_existing', verbose))
    suite.addTest(TestBlockDevice('test_statistics', verbose))

    runner = unittest2.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
