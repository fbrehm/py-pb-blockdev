#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on loop device object
'''

import os
import sys
import random
import glob
import logging

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

import pb_blockdev.loop
from pb_blockdev.loop import LoopDeviceError
from pb_blockdev.loop import LoopDevice

log = logging.getLogger('test_loop')

#==============================================================================

class TestLoopDevice(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def get_random_loop_name(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            self.skipTest("Directory %r not found." % (bd_dir))

        dirs = glob.glob(os.path.join(bd_dir, 'loop*'))
        if not dirs:
            self.skipTest("No loop devices found.")

        #devs = map(lambda x: os.path.basename(x), dirs)
        devs = []
        for dev_dir in dirs:
            devs.append(os.path.basename(dev_dir))
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]

        if self.verbose > 1:
            log.debug("Got a random loo device name %r.", devname)

        return devname

    #--------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a LoopDevice object.")

        obj = LoopDevice(
                name = 'loop0',
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("LoopDevice object:\n%s", obj)

        self.assertIsInstance(obj, LoopDevice)

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        log.info("Testing init of a LoopDevice object without a name.")

        obj = LoopDevice(
                name = None,
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("LoopDevice object:\n%s", obj)

        self.assertIsInstance(obj, LoopDevice)

    #--------------------------------------------------------------------------
    def test_existing(self):

        devname = self.get_random_loop_name()

        log.info("Testing of a LoopDevice object of the existing loop device %r.",
                devname)

        loop_dev = None

        loop_dev = LoopDevice(
                name = devname,
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("LoopDevice object:\n%s", loop_dev)
        self.assertIsInstance(loop_dev, LoopDevice)
        self.assertEqual(loop_dev.exists, True)

    #--------------------------------------------------------------------------
    def test_attach(self):

        filename = self.create_tempfile()

        log.info("Testing of attaching the temporary file %r to a newly created loop device.",
                filename)

        sudo = None
        if os.geteuid():
            sudo = True

        if not filename:
            self.skipTest("Could not create temporary file.")

        lo = None
        attached = False
        try:
            lo = LoopDevice(
                    name = None,
                    appname = self.appname,
                    verbose = self.verbose,
            )
            lo.attach(filename, sudo = sudo)
            attached = True
            if self.verbose > 2:
                log.debug("LoopDevice object:\n%s", lo)

        finally:
            if lo and attached:
                lo.detach(sudo = sudo)
            os.remove(filename)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestLoopDevice('test_object', verbose))
    suite.addTest(TestLoopDevice('test_empty_object', verbose))
    suite.addTest(TestLoopDevice('test_existing', verbose))
    suite.addTest(TestLoopDevice('test_attach', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
