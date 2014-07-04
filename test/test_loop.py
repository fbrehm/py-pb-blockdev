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

import unittest2
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

import pb_blockdev.loop
from pb_blockdev.loop import LoopDeviceError
from pb_blockdev.loop import LoopDevice

log = logging.getLogger(__name__)

#==============================================================================

class TestLoopDevice(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        self.appname = 'test_loopdev'

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
    def get_random_loop_name(self):

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            self.skipTest("Directory %r not found." % (bd_dir))

        dirs = glob.glob(os.path.join(bd_dir, 'loop*'))
        if not dirs:
            self.skipTest("No loop devices found.")

        devs = map(lambda x: os.path.basename(x), dirs)
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

        filename = self._create_tempfile()

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

    suite = unittest2.TestSuite()

    suite.addTest(TestLoopDevice('test_object', verbose))
    suite.addTest(TestLoopDevice('test_empty_object', verbose))
    suite.addTest(TestLoopDevice('test_existing', verbose))
    suite.addTest(TestLoopDevice('test_attach', verbose))

    runner = unittest2.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
