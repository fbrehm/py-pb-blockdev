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
import tempfile
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

from pb_logging.colored import ColoredFormatter

import pb_blockdev.loop
from pb_blockdev.loop import LoopDeviceError
from pb_blockdev.loop import LoopDevice

log = logging.getLogger(__name__)

#==============================================================================

class TestLoopDevice(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def _create_tempfile(self, size = 20):
        """
        Creating a temporary file of the given size. After creation the given
        count of 1 MiBytes binary zeroes are written in the file.

        @param size: the count of 1 MiBytes binary zeroes to write into this file
        @type: int

        @return: the filename of the created temporary file.
        @rtype: str

        """

        fd = None
        filename = None
        (fd, filename) = tempfile.mkstemp(suffix = '.img', prefix = 'tmp_')
        zeroes = chr(0) * 1024 * 1024

        all_ok = False
        try:
            i = 0
            while i < size:
                os.write(fd, zeroes)
                i += 1
            all_ok = True
        finally:
            os.close(fd)
            if not all_ok:
                os.remove(filename)

        if all_ok:
            return filename
        return None

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

    #--------------------------------------------------------------------------
    def test_attach(self):

        filename = self._create_tempfile()

        sudo = None
        if os.geteuid():
            sudo = True

        if not filename:
            self.fail("Could not create temporary file.")
            return

        lo = None
        attached = False
        try:
            lo = LoopDevice(
                name = None,
                appname = 'test_loopdev',
                verbose = 3,
            )
            lo.attach(filename, sudo = sudo)
            attached = True
            log.debug("Loop device object:\n%s", str(lo))

        finally:
            if lo and attached:
                lo.detach(sudo = sudo)
            os.remove(filename)

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
            'test_loop.TestLoopDevice.test_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_loop.TestLoopDevice.test_empty_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_loop.TestLoopDevice.test_existing'))
    suite.addTests(loader.loadTestsFromName(
            'test_loop.TestLoopDevice.test_attach'))

    runner = unittest.TextTestRunner(verbosity = args.verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu