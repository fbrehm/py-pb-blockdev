#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2014 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on multipath objects
'''

import os
import sys
import random
import glob
import tempfile
import logging
import locale

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import BlockdevTestcase, get_arg_verbose, init_root_logger

from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

locale.setlocale(locale.LC_ALL, '')

MY_APPNAME = 'test_multipath'

log = logging.getLogger(MY_APPNAME)


#==============================================================================
class TestMultipathDevice(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        self.appname = MY_APPNAME

    #--------------------------------------------------------------------------
    def tearDown(self):
        pass

    #--------------------------------------------------------------------------
    def test_import(self):

        log.info("Testing import of pb_blockdev.multipath ...")
        import pb_blockdev.multipath

        log.info("Testing import of GenericMultipathError from pb_blockdev.multipath ...")
        from pb_blockdev.multipath import GenericMultipathError

        log.info("Testing import of MultipathSystemError from pb_blockdev.multipath.system ...")
        from pb_blockdev.multipath.system import MultipathSystemError

        log.info("Testing import of GenericMultipathHandler from pb_blockdev.multipath ...")
        from pb_blockdev.multipath import GenericMultipathHandler

        log.info("Testing import of MultipathSystem from pb_blockdev.multipath.system ...")
        from pb_blockdev.multipath.system import MultipathSystem

    #--------------------------------------------------------------------------
    @unittest.skipUnless(
        os.path.exists('/sbin/multipathd'),
        "Binary /sbin/multipathd does not exists.")
    def test_generic_object(self):

        log.info("Testing init of a GenericMultipathHandler object.")

        from pb_blockdev.multipath import GenericMultipathHandler

        obj = GenericMultipathHandler(
            appname=self.appname,
            verbose=self.verbose,
        )
        if self.verbose > 2:
            log.debug("GenericMultipathHandler object:\n%s", obj)

        self.assertIsInstance(obj, GenericMultipathHandler)
        del obj

    #--------------------------------------------------------------------------
    @unittest.skipUnless(
        os.path.exists('/sbin/multipathd'),
        "Binary /sbin/multipathd does not exists.")
    def test_mp_system_object(self):

        log.info("Testing init of a MultipathSystem object.")

        from pb_blockdev.multipath.system import MultipathSystem

        obj = MultipathSystem(
            appname=self.appname,
            verbose=self.verbose,
        )
        if self.verbose > 2:
            log.debug("MultipathSystem object:\n%s", obj)

        self.assertIsInstance(obj, MultipathSystem)
        del obj

    #--------------------------------------------------------------------------
    @unittest.skipUnless(
        os.path.exists('/sbin/multipathd'),
        "Binary /sbin/multipathd does not exists.")
    def test_mp_system_get_maps(self):

        log.info("Testing get_maps() by a MultipathSystem object.")

        from pb_blockdev.multipath.system import MultipathSystem

        obj = MultipathSystem(
            appname=self.appname,
            verbose=self.verbose,
        )

        maps = obj.get_maps()
        if self.verbose > 2:
            log.debug("Got maps from MultipathSystem:\n%s", pp(maps))

        del obj

    #--------------------------------------------------------------------------
    @unittest.skipUnless(
        os.path.exists('/sbin/multipathd'),
        "Binary /sbin/multipathd does not exists.")
    def test_mp_system_get_paths(self):

        log.info("Testing get_paths() by a MultipathSystem object.")

        from pb_blockdev.multipath.system import MultipathSystem

        obj = MultipathSystem(
            appname=self.appname,
            verbose=self.verbose,
        )

        paths = obj.get_paths()
        if self.verbose > 2:
            log.debug("Got paths from MultipathSystem:\n%s", pp(paths))

        del obj

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestMultipathDevice('test_import', verbose))
    suite.addTest(TestMultipathDevice('test_generic_object', verbose))
    suite.addTest(TestMultipathDevice('test_mp_system_object', verbose))
    suite.addTest(TestMultipathDevice('test_mp_system_get_maps', verbose))
    suite.addTest(TestMultipathDevice('test_mp_system_get_paths', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4