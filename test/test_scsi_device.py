#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
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

from pb_logging.colored import ColoredFormatter
from pb_base.common import pp

import pb_blockdev.scsi
from pb_blockdev.scsi import ScsiDeviceError
from pb_blockdev.scsi import ScsiDevice

log = logging.getLogger(__name__)


#==============================================================================

class TestScsiDevice(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_object(self):

        try:
            obj = ScsiDevice(
                name = 'sda',
                appname = 'test_scsi_device',
                verbose = 1,
            )
            out = str(obj)
            print "\nSCSI device object: %r" % (obj.__dict__)

        except Exception, e:
            self.fail("Could not instatiate ScsiDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        try:
            obj = ScsiDevice(
                name = None,
                appname = 'test_scsi_device',
                verbose = 3,
            )
            out = str(obj)
            print "\nSCSI device object: %r" % (obj.__dict__)

        except Exception, e:
            self.fail("Could not instatiate ScsiDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_all_existing(self):

        return self.test_existing(do_all = True)

    #--------------------------------------------------------------------------
    def test_existing(self, do_all = False):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, 's*'))
        if not dirs:
            log.info("No SCSI devices found.")
            return

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

            scsi_dev = None

            try:
                scsi_dev = ScsiDevice(
                        name = dev_name,
                        appname = 'test_scsi_device',
                        verbose = 3,
                )
                dd = scsi_dev.as_dict()
                for key in dd.keys():
                    if key.startswith('_') and (not key.startswith('__')):
                        del dd[key]
                print "\nSCSI object:\n%s" % (pp(dd))

            except Exception, e:
                self.fail("Could not instatiate ScsiDevice by a %s: %s" % (
                        e.__class__.__name__, str(e)))

            if not scsi_dev.exists:
                self.fail("ScsiDevice %r should exists." % (dev_name))

#==============================================================================

if __name__ == '__main__':

    import argparse

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action = "count",
            dest = 'verbose', help = 'Increase the verbosity level')
    arg_parser.add_argument("-a", "--all", action = "store_true",
            dest = 'all', help = ('Execute verbose tests with all found ' +
                    'SCSI devices, not only with a random device.'))
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
            'test_scsi_device.TestScsiDevice.test_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_scsi_device.TestScsiDevice.test_empty_object'))
    if args.all:
        suite.addTests(loader.loadTestsFromName(
                'test_scsi_device.TestScsiDevice.test_all_existing'))
    else:
        suite.addTests(loader.loadTestsFromName(
                'test_scsi_device.TestScsiDevice.test_existing'))

    runner = unittest.TextTestRunner(verbosity = args.verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
