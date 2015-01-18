#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on the mdadm handler module
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

log = logging.getLogger('test_md')

MDADM_PATH = os.sep + os.path.join('sbin', 'mdadm')
NOT_EXISTS_MSG = "Binary %r does not exists." % (MDADM_PATH)


# =============================================================================
class MdTestcase(BlockdevTestcase):

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
    def _create_new_loop(self, size=50):
        """
        Creating a loop device object from a temporary file 50 MB and
        append it to self.loop_devs
        """

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
            self.loop_devs.append(lo)
        finally:
            if not attached:
                log.debug("Removing %r ...", filename)
                os.remove(filename)

    # -------------------------------------------------------------------------
    def test_import(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing pb_blockdev.md ...")
        import pb_blockdev.md                           # noqa

        log.debug("Importing GenericMdError from  pb_blockdev.md ...")
        from pb_blockdev.md import GenericMdError       # noqa

        log.debug("Importing MdadmError from  pb_blockdev.md ...")
        from pb_blockdev.md import MdadmError           # noqa

        log.debug("Importing GenericMdHandler from  pb_blockdev.md ...")
        from pb_blockdev.md import GenericMdHandler     # noqa

        log.debug("Importing MdAdm from  pb_blockdev.md.admin ...")
        from pb_blockdev.md.admin import MdAdm          # noqa

        log.debug("Importing MdDevice from  pb_blockdev.md.device ...")
        from pb_blockdev.md.device import MdDevice      # noqa

    # -------------------------------------------------------------------------
    def test_transform_uuid(self):

        log.info("Test transforming an UUID to the MD Raid format and back.")

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

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(MDADM_PATH), NOT_EXISTS_MSG)
    def test_handler_object(self):

        log.info("Test init of a GenericMdHandler object ...")

        from pb_blockdev.md import GenericMdHandler

        try:
            hdlr = GenericMdHandler(
                appname=self.appname,
                verbose=self.verbose,
            )
        except CommandNotFoundError as e:
            log.info(str(e))
            return

        if self.verbose > 1:
            log.debug("repr of GenericMdHandler object: %r", hdlr)

        if self.verbose > 2:
            log.debug("GenericMdHandler object:\n%s", pp(hdlr.as_dict(True)))

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(MDADM_PATH), NOT_EXISTS_MSG)
    def test_mdadm_lock(self):

        log.info("Test global lock of a GenericMdHandler object ...")

        from pb_blockdev.md import GenericMdHandler

        try:
            hdlr = GenericMdHandler(
                appname=self.appname,
                verbose=self.verbose,
            )
        except CommandNotFoundError as e:
            log.info(str(e))
            return

        hdlr.lock_global()
        msg = "Object hdlr.global_lock is not a instance of PbLock."
        self.assertIsInstance(hdlr.global_lock, PbLock, msg)
        lockfile = hdlr.global_lock.lockfile
        log.debug("Lockfile: %r.", lockfile)
        if not os.path.exists(lockfile):
            msg = "Lockfile %r does not exists."
            self.fail(msg % (lockfile))
        if self.verbose > 2:
            log.debug(
                "Global lock object:\n%s",
                pp(hdlr.global_lock.as_dict(True)))

        hdlr.global_lock = None
        if os.path.exists(lockfile):
            msg = "Lockfile %r still exists."
            self.fail(msg % (lockfile))

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(MDADM_PATH), NOT_EXISTS_MSG)
    def test_mdadm_object(self):

        log.info("Test init of a MdAdm object ...")

        from pb_blockdev.md.admin import MdAdm

        try:
            mdadm = MdAdm(
                appname=self.appname,
                verbose=self.verbose,
            )
        except CommandNotFoundError as e:
            log.info(str(e))
            return

        if self.verbose > 1:
            log.debug("repr of MdAdm object: %r", mdadm)

        if self.verbose > 2:
            log.debug("MdAdm object:\n%s", pp(mdadm.as_dict(True)))

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(MDADM_PATH), NOT_EXISTS_MSG)
    def test_zero_superblock(self):

        log.info("Test execute of zero_superblock with a MdAdm object ...")

        from pb_blockdev.md.admin import MdAdm

        try:
            mdadm = MdAdm(
                appname=self.appname,
                verbose=self.verbose,
            )
        except CommandNotFoundError as e:
            log.info(str(e))
            return

        if self.verbose > 3:
            log.debug("MdAdm object:\n%s", pp(mdadm.as_dict(True)))

        self._create_new_loop()
        loop = self.loop_devs[0]

        no_dump = True
        if os.geteuid() == 0:
            no_dump = False

        mdadm.zero_superblock(loop, no_dump=no_dump)

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(MDADM_PATH), NOT_EXISTS_MSG)
    def test_examine(self):

        from pb_blockdev.base import BlockDevice
        from pb_blockdev.md.admin import MdAdm

        try:
            mdadm = MdAdm(
                appname=self.appname,
                verbose=self.verbose,
            )
        except CommandNotFoundError as e:
            log.info(str(e))
            return

        self._create_new_loop()
        loop = self.loop_devs[0]

        log.info("Test examining MD superblock of an empty device.")
        sb = mdadm.examine(loop)
        self.assertIsNone(sb, "There may be no superblock on an empty device.")

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            self.skipTest("Directory %r not found." % (bd_dir))
        md_dev_dirs = glob.glob(os.path.join(bd_dir, 'md*'))
        if not md_dev_dirs:
            self.skipTest("No MD raids with componenets found.")
        components = []
        for md_dev_dir in md_dev_dirs:
            cdirs = glob.glob(os.path.join(md_dev_dir, 'md', 'dev-*'))
            for cdir in cdirs:
                block_link = os.path.join(cdir, 'block')
                devname = os.path.basename(os.readlink(block_link))
                components.append(devname)
        if not components:
            self.skipTest("No MD component devices found.")
        if self.verbose > 2:
            log.debug("Found MD component devices: %s", pp(components))
        index = random.randint(0, len(components) - 1)
        devname = components[index]
        blockdev = BlockDevice(
            name=devname,
            appname=self.appname,
            verbose=self.verbose,
        )
        log.debug("Examining blockdevice %r ...", blockdev.device)
        if self.verbose > 2:
            log.debug("BlockDevice object to examine:\n%s", blockdev)

        sb = mdadm.examine(blockdev)
        if self.verbose > 2:
            log.debug(
                "Got MD superblock information of %r:\n%s",
                blockdev.device, sb)
        log.debug("Finished examining.")

    # -------------------------------------------------------------------------
    @unittest.skipUnless(os.path.exists(MDADM_PATH), NOT_EXISTS_MSG)
    def test_md_device(self):

        from pb_blockdev.md.device import MdDevice

        log.info("Test MD device object.")

        bd_dir = os.sep + os.path.join('sys', 'block')
        if not os.path.isdir(bd_dir):
            self.skipTest("Directory %r not found." % (bd_dir))
        md_dev_dirs = glob.glob(os.path.join(bd_dir, 'md*'))

        if md_dev_dirs:
            index = random.randint(0, len(md_dev_dirs) - 1)
            dev_dir = md_dev_dirs[index]
            md_name = os.path.basename(dev_dir)
        else:
            md_name = 'md0'

        md = MdDevice(
            name=md_name,
            appname=self.appname,
            verbose=self.verbose,
        )

        if self.verbose > 2:
            log.debug("Got a MD device:\n%s", pp(md.as_dict(True)))

        if md.exists:
            log.info("Test getting details from MD device %s.", md_name)
            details = md.get_details()
            if self.verbose > 2:
                log.debug("Details of %s:\n%s", md_name, details)


# =============================================================================


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
    suite.addTest(MdTestcase('test_mdadm_lock', verbose))
    suite.addTest(MdTestcase('test_mdadm_object', verbose))
    suite.addTest(MdTestcase('test_zero_superblock', verbose))
    suite.addTest(MdTestcase('test_examine', verbose))
    suite.addTest(MdTestcase('test_md_device', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
