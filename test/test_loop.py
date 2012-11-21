#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on loop device object
'''

import unittest
import os
import sys
import random
import glob

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import pb_blockdev.loop
from pb_blockdev.loop import LoopDeviceError
from pb_blockdev.loop import LoopDevice

#==============================================================================

class TestLoopDevice(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_object(self):

        try:
            obj = LoopDevice(
                name = 'loop0',
                appname = 'test_loopdev',
                verbose = 1,
            )
            out = str(obj)
            print "\nLoop device object: %r" % (obj.__dict__)

        except Exception, e:
            self.fail("Could not instatiate LoopDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        try:
            obj = LoopDevice(
                name = None,
                appname = 'test_loopdev',
                verbose = 1,
            )
            out = str(obj)
            print "\nLoop device object: %r" % (obj.__dict__)

        except Exception, e:
            self.fail("Could not instatiate LoopDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_existing(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, 'loop*'))
        devs = map(lambda x: os.path.basename(x), dirs)
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]

        loop_dev = None

        try:
            loop_dev = LoopDevice(
                name = devname,
                appname = 'test_loopdev',
                verbose = 3,
            )
            print "\nLoop device object:\n%s" % (str(loop_dev))

        except Exception, e:
            self.fail("Could not instatiate LoopDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

        if not loop_dev.exists:
            self.fail("LoopDevice %r should exists." % (devname))

#==============================================================================

if __name__ == '__main__':

    import argparse

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action = "count",
            dest = 'verbose', help = 'Increase the verbosity level')
    args = arg_parser.parse_args()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_loop.TestLoopDevice.test_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_loop.TestLoopDevice.test_empty_object'))
#    suite.addTests(loader.loadTestsFromName(
#            'test_loop.TestLoopDevice.test_existing'))

    runner = unittest.TextTestRunner(verbosity = args.verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
