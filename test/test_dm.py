#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on devicemapper device objects
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

import pb_blockdev.dm
from pb_blockdev.dm import DmDeviceError
from pb_blockdev.dm import DmDeviceInitError
from pb_blockdev.dm import DeviceMapperDevice

log = logging.getLogger(__name__)

#==============================================================================

class TestDmDevice(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_object(self):

        try:
            obj = DeviceMapperDevice(
                name = 'dm-0',
                appname = 'test_dmdev',
                verbose = 1,
            )
            out = str(obj)
            print "\nDevicemapper device object: %r" % (obj.__dict__)

        except Exception, e:
            self.fail("Could not instatiate DeviceMapperDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        try:
            obj = DeviceMapperDevice(
                name = None,
                appname = 'test_dmdev',
                verbose = 3,
            )
            out = str(obj)
            print "\nnDevicemapper device object: %r" % (obj.__dict__)

        except DmDeviceInitError, e:
            log.info("Init of a DeviceMapperDevice object not successful:\n\t%s",
                    str(e))

        except Exception, e:
            self.fail("Could not instatiate DeviceMapperDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

        else:
            self.fail("Init of an empty DeviceMapperDevice object should " +
                    "not be successful.")

    #--------------------------------------------------------------------------
    def test_existing(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            return

        dirs = glob.glob(os.path.join(bd_dir, 'dm-*'))
        if not dirs:
            log.info("No devicemapper devices found.")
            return
        devs = map(lambda x: os.path.basename(x), dirs)
        index = random.randint(0, len(devs) - 1)
        devname = devs[index]

        dm_dev = None

        try:
            dm_dev = DeviceMapperDevice(
                name = devname,
                appname = 'test_dmdev',
                verbose = 3,
            )
            dd = dm_dev.as_dict()
            for key in dd.keys():
                if key.startswith('_') and (not key.startswith('__')):
                    del dd[key]
            print "\nDeviceMapperDevice object:\n%s" % (pp(dd))

        except Exception, e:
            self.fail("Could not instatiate DeviceMapperDevice by a %s: %s" % (
                    e.__class__.__name__, str(e)))

        if not dm_dev.exists:
            self.fail("DeviceMapperDevice %r should exists." % (devname))

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
            'test_dm.TestDmDevice.test_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_dm.TestDmDevice.test_empty_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_dm.TestDmDevice.test_existing'))

    runner = unittest.TextTestRunner(verbosity = args.verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
