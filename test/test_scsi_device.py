#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2013 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on Scsi device objects
'''

import unittest
import os
import sys
import random
import glob
import tempfile
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import BlockdevTestcase, get_arg_verbose, init_root_logger

from pb_base.common import pp

import pb_blockdev.scsi
from pb_blockdev.scsi import ScsiDeviceError
from pb_blockdev.scsi import ScsiDevice

log = logging.getLogger(__name__)

#==============================================================================

class TestScsiDevice(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        self.appname = 'test_scsi_device'

    #--------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a ScsiDevice object.")

        obj = ScsiDevice(
                name = 'sda',
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("ScsiDevice object:\n%s", obj)

        self.assertIsInstance(obj, ScsiDevice)
        del obj

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        log.info("Testing init of a ScsiDevice object without a name.")

        obj = ScsiDevice(
                name = None,
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("ScsiDevice object:\n%s", obj)

        self.assertIsInstance(obj, ScsiDevice)

    #--------------------------------------------------------------------------
    def test_all_existing(self):

        return self.test_existing(do_all = True)

    #--------------------------------------------------------------------------
    def test_existing(self, do_all = False):

        if do_all:
            log.info("Testing of all found ScsiDevices on the system.")
        else:
            log.info("Testing of a single existing ScsiDevices.") 

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, 's*'))
        if not dirs:
            self.skipTest("No SCSI devices found.")

        devs = map(lambda x: os.path.basename(x), dirs)

        dev_names = []
        for dev in devs:
            if ScsiDevice.isa(dev):
                dev_names.append(dev)

        devices = []
        if do_all:
            devices = dev_names
        else:
            index = random.randint(0, len(dev_names) - 1)
            devices.append(dev_names[index])

        for dev_name in devices:

            log.debug("Testing of ScsiDevices %r ...", dev_name)

            scsi_dev = ScsiDevice(
                    name = dev_name,
                    appname = self.appname,
                    verbose = self.verbose,
            )
            log.debug("ScsiDevice: %r", scsi_dev.name)
            if self.verbose > 3 or (self.verbose > 2 and not do_all):
                log.debug("ScsiDevice object:\n%s", scsi_dev)
            self.assertIsInstance(scsi_dev, ScsiDevice)
            self.assertEqual(scsi_dev.exists, True)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestScsiDevice('test_object', verbose))
    suite.addTest(TestScsiDevice('test_empty_object', verbose))
    suite.addTest(TestScsiDevice('test_all_existing', verbose))
    suite.addTest(TestScsiDevice('test_existing', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
