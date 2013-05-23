#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2013 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on disk objects
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

import pb_blockdev.disk
from pb_blockdev.disk import DiskError
from pb_blockdev.disk import Disk

log = logging.getLogger(__name__)

#==============================================================================

class TestDisk(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        self.appname = 'test_disk'

    #--------------------------------------------------------------------------
    def test_object(self):

        log.info("Testing init of a Disk object.")

        obj = Disk(
                name = 'sda',
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("Disk object:\n%s", obj)

        self.assertIsInstance(obj, Disk)
        del obj

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        log.info("Testing init of a Disk object without a name.")

        obj = Disk(
                name = None,
                appname = self.appname,
                verbose = self.verbose,
        )
        if self.verbose > 2:
            log.debug("Disk object:\n%s", obj)

        self.assertIsInstance(obj, Disk)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestDisk('test_object', verbose))
    suite.addTest(TestDisk('test_empty_object', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
