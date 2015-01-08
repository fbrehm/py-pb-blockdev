#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on base blockdevice object
'''

import os
import sys
import random
import glob
import logging
import tempfile
import shutil

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import BlockdevTestcase, get_arg_verbose, init_root_logger

from pb_base.common import pp
from pb_base.common import to_unicode_or_bust, to_utf8_or_bust

import pb_blockdev.base
from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDeviceStatistic
from pb_blockdev.base import BlockDevice
from pb_blockdev.base import format_bytes, size_to_sectors

log = logging.getLogger('test_blockdev')

A_KILO = 1024
if sys.version_info[0] <= 2:
    A_KILO = long(1024)

#==============================================================================

class TestBlockDevice(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):

        pass

    #--------------------------------------------------------------------------
    def get_random_blockdev_name(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            self.skipTest("Directory %r not found." % (bd_dir))

        dirs = glob.glob(os.path.join(bd_dir, '*'))
        devs = []
        for dev in map(lambda x: os.path.basename(x), dirs):
            devs.append(dev)
        #devs = map(lambda x: os.path.basename(x), dirs)
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
            ((A_KILO * A_KILO * A_KILO * A_KILO * A_KILO), 'GiB', (A_KILO * A_KILO), float(A_KILO * A_KILO)),
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
            msg = "Failed formating bytes %r into %r, expected result: %r, got result: %r" % (
                    val, unit, exp_result, result)
            self.assertEqual(result, exp_result, msg)

            log.debug("Converting %r into %r as float, expected result: %r.",
                    val, unit, exp_result_f)
            result_f = format_bytes(val, unit, True)
            log.debug("Got converted float result: %r", result_f)
            msg = "Failed formating bytes %r into %r as float, expected result: %r, got result: %r" % (
                    val, unit, exp_result_f, result_f)
            self.assertEqual(result_f, exp_result_f, msg)

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

        long_val = (2, 'GiB', None,  4096 * 1024)
        if sys.version_info[0] <= 2:
            long_val = (long(2), 'GiB', None,  long(4096 * 1024))

        values = (
            (1024, 'B',   None,    2),
            (1024, 'B',    512,    2),
            (1024, 'B',   1024,    1),
            (   1, 'MiB', None, 2048),
            (   2, 'MiB', 4096,  512),
            (   1, 'MB',  None, 1953),
            long_val,
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

    #--------------------------------------------------------------------------
    @unittest.skipUnless(os.geteuid() == 0, "Only root may perform mknod operations.")
    def test_mknod(self):

        devname = self.get_random_blockdev_name()
        blockdev = BlockDevice(
                name = devname,
                appname = self.appname,
                verbose = self.verbose,
        )

        tmpdir = tempfile.mkdtemp(prefix = 'dev_tmp.')
        device = os.path.join(tmpdir, blockdev.name)
        log.info("Testing creation of block device file %r ...", device)

        try:
            blockdev.mknod(device)
        finally:
            if self.verbose > 2:
                log.debug("Removing directory %r recursive ...", tmpdir)
            shutil.rmtree(tmpdir, True)

    #--------------------------------------------------------------------------
    def test_fuser(self):

        from pb_blockdev.base import FuserError

        devname = self.get_random_blockdev_name()
        blockdev = BlockDevice(
                name = devname,
                appname = self.appname,
                verbose = self.verbose,
        )

        fd = None
        filename = None
        size = 20
        zeroes = to_utf8_or_bust(chr(0) * 1024 * 1024)
        (fd, filename) = tempfile.mkstemp(suffix = '.data', prefix = 'tmp_')

        try:
            log.debug("Created temporary file %r, writing in it.", filename)
            i = 0
            while i < size:
                os.write(fd, zeroes)
                i += 1

            log.info("Test fuser to an opened file ...")
            pids = blockdev.opened_by_processes(filename)
            log.debug("Got PIDs of opening processes of %r: %r", filename, pids)
            self.assertIsInstance(pids, list, "Method opened_by_processes() should return a list")
            self.assertGreaterEqual(
                len(pids), 1, "Method opened_by_processes() should return a list with one element.")
            self.assertIsInstance(
                pids[0], int, "The elements of the result list of opened_by_processes() shoul be integers.")


            log.info("Test fuser to a closed file ...")
            os.close(fd)
            fd = None
            pids = blockdev.opened_by_processes(filename)
            log.debug("Got PIDs of opening processes of %r: %r", filename, pids)
            self.assertIsInstance(pids, list, "Method opened_by_processes() should return a list")
            self.assertEqual(
                len(pids), 0, "Method opened_by_processes() should return a empty list.")

            log.info("Test fuser to a not existing file ...")
            os.remove(filename)
            with self.assertRaises(FuserError) as cm:
                pids = blockdev.opened_by_processes(filename)
                log.debug("Got PIDs of opening processes of %r: %r", filename, pids)
            e = cm.exception
            log.debug("%s raised on opened_by_processes() with not existing file %r: %s",
                    e.__class__.__name__, filename, e)

        finally:
            if fd:
                log.debug("Closing temporary file %r.", filename)
                os.close(fd)
            if filename and os.path.exists(filename):
                log.debug("Removing temporary file %r.", filename)
                os.remove(filename)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestBlockDevice('test_format_bytes', verbose))
    suite.addTest(TestBlockDevice('test_size_to_sectors', verbose))
    suite.addTest(TestBlockDevice('test_object', verbose))
    suite.addTest(TestBlockDevice('test_existing', verbose))
    suite.addTest(TestBlockDevice('test_statistics', verbose))
    suite.addTest(TestBlockDevice('test_mknod', verbose))
    suite.addTest(TestBlockDevice('test_fuser', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
