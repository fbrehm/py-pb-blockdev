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

from pb_logging.colored import ColoredFormatter
from pb_base.common import pp

import pb_blockdev.base
from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDevice

log = logging.getLogger(__name__)

#==============================================================================

class TestBlockDevice(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_object(self):

        try:
            obj = BlockDevice(
                name = 'sda',
                appname = 'test_blockdev',
                verbose = 1,
            )
            print "\nBase blockdevice object: %r" % (obj.__dict__)

        except Exception, e:
            self.fail("Could not instatiate BlockDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_existing(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, '*'))
        devs = map(lambda x: os.path.basename(x), dirs)
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]
        blockdev = None

        try:
            blockdev = BlockDevice(
                name = devname,
                appname = 'test_blockdev',
                verbose = 3,
            )
            dd = blockdev.as_dict()
            for key in dd.keys():
                if key.startswith('_') and (not key.startswith('__')):
                    del dd[key]
            print "\nBlockdevice object:\n%s" % (pp(dd))

        except Exception, e:
            self.fail("Could not instatiate BlockDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

        if not blockdev.exists:
            self.fail("Blockdevice %r should exists." % (devname))

    #--------------------------------------------------------------------------
    def test_statistics(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, '*'))
        devs = map(lambda x: os.path.basename(x), dirs)
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]
        blockdev = None

        try:
            blockdev = BlockDevice(
                name = devname,
                appname = 'test_blockdev',
                verbose = 3,
            )
            stats = blockdev.get_statistics()
            dd = stats.as_dict()
            for key in dd.keys():
                if key.startswith('_') and (not key.startswith('__')):
                    del dd[key]
            print "\nBlockdevice statistics of %r:\n%s" % (
                    blockdev.device, pp(dd))

        except Exception, e:
            self.fail("Could not instatiate BlockDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

#==============================================================================

if __name__ == '__main__':

    import argparse

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action = "count",
            dest = 'verbose', help = 'Increase the verbosity level')
    args = arg_parser.parse_args()

    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)
    if args.verbose:
         root_log.setLevel(logging.DEBUG)

    appname = os.path.basename(sys.argv[0])
    format_str = appname + ': '
    if args.verbose:
        if args.verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    formatter = ColoredFormatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if args.verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_blockdev.TestBlockDevice.test_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_blockdev.TestBlockDevice.test_existing'))
    suite.addTests(loader.loadTestsFromName(
            'test_blockdev.TestBlockDevice.test_statistics'))

    runner = unittest.TextTestRunner(verbosity = args.verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
