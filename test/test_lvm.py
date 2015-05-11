#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on the lvm handler module
'''

import os
import sys
import logging
import uuid
import glob
import random

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

from general import BlockdevTestcase, get_arg_verbose, init_root_logger

from pb_base.handler import CommandNotFoundError
from pb_base.common import pp

from pb_base.handler.lock import PbLock

from pb_blockdev.loop import LoopDevice

log = logging.getLogger('test_lvm')

LVM_PATH = os.sep + os.path.join('sbin', 'lvm')
NOT_EXISTS_MSG = "Binary %r does not exists." % (LVM_PATH)


# =============================================================================
class LvmTestcase(BlockdevTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):

        self.loop_devs = []

    # -------------------------------------------------------------------------
    def tearDown(self):

        sudo = None
        if os.geteuid():
            sudo = True

        i = -1
        for loop in self.loop_devs:
            i += 1
            if loop and loop.attached:
                # Detaching and removing backing file
                filename = loop.backing_file
                loop.detach(sudo=sudo)
                log.debug("Removing %r ...", filename)
                os.remove(filename)
            self.loop_devs[i] = None

        self.loop_devs = []

    # -------------------------------------------------------------------------
    def test_import(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing pb_blockdev.lvm ...")
        import pb_blockdev.lvm                           # noqa

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(LVM_PATH), NOT_EXISTS_MSG)
    def test_handler_object(self):

        log.info("Test init of a GenericLvmHandler object ...")

        from pb_blockdev.lvm import GenericLvmHandler

        try:
            hdlr = GenericLvmHandler(
                appname=self.appname,
                verbose=self.verbose,
            )
        except CommandNotFoundError as e:
            log.info(str(e))
            return

        if self.verbose > 1:
            log.debug("repr of GenericLvmHandler object: %r", hdlr)

        if self.verbose > 2:
            log.debug("GenericLvmHandler object:\n%s", pp(hdlr.as_dict(True)))

# =============================================================================


if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(LvmTestcase('test_import', verbose))
    suite.addTest(LvmTestcase('test_handler_object', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
