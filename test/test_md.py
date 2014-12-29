#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2014 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on the mdadm handler module
'''

import os
import sys
import logging
import tempfile
import time
import uuid

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

MDADM_PATH = os.sep + os.path.join('sbin', 'mdadm')
NOT_EXISTS_MSG = "Binary %r does not exists." % (MDADM_PATH)

#==============================================================================
class MdTestcase(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_import(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing pb_blockdev.md ...")
        import pb_blockdev.md

        log.debug("Importing GenericMdError from  pb_blockdev.md ...")
        from pb_blockdev.md import GenericMdError

        log.debug("Importing MdadmError from  pb_blockdev.md ...")
        from pb_blockdev.md import MdadmError

        log.debug("Importing GenericMdHandler from  pb_blockdev.md ...")
        from pb_blockdev.md import GenericMdHandler

    #--------------------------------------------------------------------------
    def test_transform_uuid(self):

        log.info("Test transforming an UUID to the MD Raid format and back.")

        import pb_blockdev.md
        from pb_blockdev.md import uuid_to_md, uuid_from_md

        uuid_src = uuid.UUID('f999f69e-7a5a-4abc-964c-e6e3c6858961')
        uuid_exp_md = 'f999f69e:7a5a4abc:964ce6e3:c6858961'

        log.debug("Transforming %r, expected: %r.", uuid_src, uuid_exp_md)
        uuid_got_md = uuid_to_md(uuid_src)
        msg = "Expectd: %r, Got: %r" % (uuid_exp_md, uuid_got_md)
        self.assertEqual(uuid_exp_md, uuid_got_md, msg)

        log.debug("Transforming %r into UUID, expected: %r.", uuid_exp_md, uuid_src)
        uuid_got_uuid = uuid_from_md(uuid_exp_md)
        msg = "Expectd: %r, Got: %r" % (uuid_src, uuid_got_uuid)
        self.assertEqual(uuid_src, uuid_got_uuid, msg)

    #--------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(MDADM_PATH), NOT_EXISTS_MSG)
    def test_handler_object(self):

        log.info("Test init of a GenericMdHandler object ...")

        import pb_blockdev.md
        from pb_blockdev.md import GenericMdHandler

        try:
            hdlr = GenericMdHandler(verbose = self.verbose)
        except CommandNotFoundError, e:
            log.info(str(e))
            return

        if self.verbose > 1:
            log.debug("repr of GenericMdHandler object: %r", hdlr)

        if self.verbose > 2:
            log.debug("GenericMdHandler object:\n%s", pp(hdlr.as_dict(True)))


#==============================================================================


if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(MdTestcase('test_import', verbose))
    suite.addTest(MdTestcase('test_transform_uuid', verbose))
    suite.addTest(MdTestcase('test_handler_object', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)


#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
