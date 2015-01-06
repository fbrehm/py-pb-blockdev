#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on devicemapper device objects
'''

import os
import sys
import random
import glob
import tempfile
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

import pb_blockdev.dm
from pb_blockdev.dm import DmDeviceError
from pb_blockdev.dm import DmDeviceInitError
from pb_blockdev.dm import DeviceMapperDevice

log = logging.getLogger('test_dm')

#==============================================================================

class TestDmDevice(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def get_random_dm_name(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            self.skipTest("Directory %r not found." % (bd_dir))

        dirs = glob.glob(os.path.join(bd_dir, 'dm-*'))
        if not dirs:
            self.skipTest("No Devicemapper devices found.")

        devs = []
        for dev_dir in dirs:
            devs.append(os.path.basename(dev_dir))
        if self.verbose > 2:
            log.debug("Found DM devices: %s", pp(devs))
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]

        if self.verbose > 1:
            log.debug("Got a random devicemapper name %r.", devname)

        return devname

    #--------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a DeviceMapperDevice object.")

        obj = DeviceMapperDevice(
                name = 'dm-0',
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("DeviceMapperDevice object:\n%s", obj)

        self.assertIsInstance(obj, DeviceMapperDevice)
        del obj

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        log.info("Testing failing init of a DeviceMapperDevice object without a name.")

        obj = None
        with self.assertRaises(DmDeviceInitError) as cm:
            obj = DeviceMapperDevice(
                    name = None,
                    appname = self.appname,
                    verbose = self.verbose,
            )

        e = cm.exception
        log.debug("%s raised on init of an DeviceMapperDevice with no name: %s",
                'DmDeviceInitError', e)

    #--------------------------------------------------------------------------
    def test_existing(self):

        devname = self.get_random_dm_name()

        log.info("Testing of a DeviceMapperDevice object of the existing DM device %r.",
                devname)

        dm_dev = DeviceMapperDevice(
            name = devname,
            appname = self.appname,
            verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("DeviceMapperDevice object:\n%s", dm_dev)
        self.assertIsInstance(dm_dev, DeviceMapperDevice)
        self.assertEqual(dm_dev.exists, True)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestDmDevice('test_object', verbose))
    suite.addTest(TestDmDevice('test_empty_object', verbose))
    suite.addTest(TestDmDevice('test_existing', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
