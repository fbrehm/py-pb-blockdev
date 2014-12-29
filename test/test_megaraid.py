#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2014 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on the megaraid mhandler module
'''

import os
import sys
import logging
import tempfile
import time

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import BlockdevTestcase, get_arg_verbose, init_root_logger

from pb_base.handler import CommandNotFoundError
from pb_base.common import pp

log = logging.getLogger(__name__)

#==============================================================================
class MegaraidTestcase(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_import(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing pb_blockdev.megaraid ...")
        import pb_blockdev.megaraid

        log.debug("Importing MegaraidrError from  pb_blockdev.megaraid ...")
        from pb_blockdev.megaraid import MegaraidError

        log.debug("Importing MegaraidHandlerError from  pb_blockdev.megaraid ...")
        from pb_blockdev.megaraid import MegaraidHandlerError

        log.debug("Importing MegaraidHandler from  pb_blockdev.megaraid.handler ...")
        from pb_blockdev.megaraid.handler import MegaraidHandler

    #--------------------------------------------------------------------------
    def test_handler_object(self):

        log.info("Test init of a MegaraidHandler object ...")

        import pb_blockdev.megaraid
        from pb_blockdev.megaraid.handler import MegaraidHandler

        try:
            hdlr = MegaraidHandler(verbose = self.verbose)
        except CommandNotFoundError, e:
            log.info(str(e))
            return

        if self.verbose > 1:
            log.debug("repr of MegaraidHandler object: %r", hdlr)

        if self.verbose > 2:
            log.debug("MegaraidHandler object:\n%s", pp(hdlr.as_dict(True)))

    #--------------------------------------------------------------------------
    def test_exec_megacli(self):

        log.info("Test execute of MegaCLI ...")

        import pb_blockdev.megaraid
        from pb_blockdev.megaraid.handler import MegaraidHandler

        try:
            hdlr = MegaraidHandler(verbose = self.verbose)
        except CommandNotFoundError, e:
            log.info(str(e))
            return

        result = hdlr.exec_megacli('-adpCount')
        log.debug("Got result of 'MegaCLI -adpCount':\n%s", pp(result))

    #--------------------------------------------------------------------------
    def test_adapter_count(self):

        log.info("Test execute of adapter_count() ...")

        import pb_blockdev.megaraid
        from pb_blockdev.megaraid.handler import MegaraidHandler

        try:
            hdlr = MegaraidHandler(verbose = self.verbose)
        except CommandNotFoundError, e:
            log.info(str(e))
            return

        count = hdlr.adapter_count()
        s = 's'
        if count == 1:
            s = ''
        log.debug("The test found %d MegaRaid controller%s.", count, s)

#==============================================================================


if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(MegaraidTestcase('test_import', verbose))
    suite.addTest(MegaraidTestcase('test_handler_object', verbose))
    suite.addTest(MegaraidTestcase('test_exec_megacli', verbose))
    suite.addTest(MegaraidTestcase('test_adapter_count', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)


#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
