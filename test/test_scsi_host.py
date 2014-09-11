#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2014 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on the scsi_host module
'''

import unittest
import os
import sys
import logging
import tempfile
import time

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import BlockdevTestcase, get_arg_verbose, init_root_logger

from pb_base.handler import CommandNotFoundError
from pb_base.common import pp

log = logging.getLogger(__name__)

#==============================================================================
class ScsiHostTestcase(BlockdevTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_import(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing pb_blockdev.scsi_host ...")
        import pb_blockdev.scsi_host

        log.debug("Importing ScsiHostError from pb_blockdev.scsi_host ...")
        from pb_blockdev.scsi_host import ScsiHostError

        log.debug("Importing ScsiHost from pb_blockdev.scsi_host ...")
        from pb_blockdev.scsi_host import ScsiHost

    #--------------------------------------------------------------------------
    def test_scsi_host_object(self):

        log.info("Test init of a ScsiHost object ...")

        import pb_blockdev.scsi_host
        from pb_blockdev.scsi_host import ScsiHost

        scsi_host = ScsiHost(0, verbose = self.verbose)

        if self.verbose > 1:
            log.debug("repr of ScsiHost object: %r", scsi_host)

        if self.verbose > 2:
            log.debug("ScsiHost object:\n%s", pp(scsi_host.as_dict(True)))

    #--------------------------------------------------------------------------
    def test_get_all_scsi_hosts(self):

        log.info("Test getting of all ScsiHosts ...")

        import pb_blockdev.scsi_host
        from pb_blockdev.scsi_host import ScsiHost
        from pb_blockdev.scsi_host import get_scsi_hosts

        scsi_hosts = get_scsi_hosts(verbose = self.verbose)

        if self.verbose:
            hostnames = map(lambda x: x.hostname, scsi_hosts)
            log.debug("Got ScsiHost list:\n%s", pp(hostnames))

    #--------------------------------------------------------------------------
    def test_search_blockdevices(self):

        log.info("Test searching for target blockdevices ...")

        import pb_blockdev.scsi_host
        from pb_blockdev.scsi_host import ScsiHost
        from pb_blockdev.scsi_host import get_scsi_hosts

        scsi_hosts = get_scsi_hosts(verbose = self.verbose)

        if not scsi_hosts:
            log.debug("No SCSI hosts found.")

        for scsi_host in scsi_hosts:
            if not scsi_host.luns:
                continue

            for hbtl in scsi_host.luns:
                self.assertEqual(hbtl.host, scsi_host.host_id)
                blockdev = scsi_host.lun_blockdevice(
                    hbtl.bus, hbtl.target, hbtl.lun)
                if not blockdev:
                    continue

                log.debug("Found blockdevice %r for '%s'.", blockdev, hbtl)

#==============================================================================


if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(ScsiHostTestcase('test_import', verbose))
    suite.addTest(ScsiHostTestcase('test_scsi_host_object', verbose))
    suite.addTest(ScsiHostTestcase('test_get_all_scsi_hosts', verbose))
    suite.addTest(ScsiHostTestcase('test_search_blockdevices', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)


#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
