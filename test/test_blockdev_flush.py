#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on flushing a blockdevice
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

log = logging.getLogger('test_blockdev_flush')

# =============================================================================
class BlockdevFlushTestcase(BlockdevTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):

        self.loop_dev = None

    # -------------------------------------------------------------------------
    def tearDown(self):

        sudo = None
        if os.geteuid():
            sudo = True

        if self.loop_dev and self.loop_dev.attached:
            # Detaching and removing backing file
            filename = self.loop_dev.backing_file
            self.loop_dev.detach(sudo=sudo)
            log.debug("Removing %r ...", filename)
            os.remove(filename)
        self.loop_dev = None

    # -------------------------------------------------------------------------
    def _create_new_loop(self, size=50):
        """
        Creating a loop device object from a temporary file 50 MB and
        append it to self.loop_devs
        """

        if self.loop_dev and self.loop_dev.attached:
            log.warn("Loopdevice %r allready exists.", self.loop_dev.name)

        filename = self.create_tempfile(size=size)
        sudo = None
        if os.geteuid():
            sudo = True
        if not filename:
            self.skipTest("Could not create temporary file.")

        lo = None
        attached = False

        try:
            lo = LoopDevice(
                name=None,
                appname=self.appname,
                verbose=self.verbose,
            )
            lo.attach(filename, sudo=sudo)
            attached = True
            log.debug("Created loop device %r -> %r.", lo.name, filename)
            if self.verbose > 3:
                log.debug("LoopDevice object:\n%s", lo)
            self.loop_dev = lo
        finally:
            if not attached:
                log.debug("Removing %r ...", filename)
                os.remove(filename)

    # -------------------------------------------------------------------------
    def test_flush(self):

        if os.geteuid():
            self.skipTest("You must be root to execute this test.")

        log.info("Test flushing a blockdevice ...")

        from pb_blockdev.base import BlockDevice

        self._create_new_loop()
        devname = self.loop_dev.name

        blockdev = BlockDevice(
            name=devname,
            appname=self.appname,
            verbose=self.verbose,
        )
        if not blockdev.blockdev_command:
            self.skipTest("Binary 'blockdev' not found.")

        block = os.urandom(1024 * 1024)

        log.debug("writing into blockdevice %r ...", blockdev.device)
        with blockdev.open('w') as fh:
            i = 1
            while i <= 10:
                log.debug("writing No. %02d...", i)
                fh.write(block)
                i += 1
        log.debug("Closed blockdevice %r.", blockdev.device)
        log.info("Test flushing blockdevice %r ...", blockdev.device)
        blockdev.flush()

# =============================================================================


if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(BlockdevFlushTestcase('test_flush', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
