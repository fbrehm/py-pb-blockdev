#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a loop device class
"""

# Standard modules
import sys
import os
import logging
import re
import glob

from gettext import gettext as _

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_blockdev.base import BlockDeviceError
from pb_blockdev.base import BlockDevice

__version__ = '0.3.1'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

LOSETUP_CMD = os.sep + os.path.join('sbin', 'losetup')

#==============================================================================
class LoopDeviceError(BlockDeviceError):
    """
    Base error class for all exceptions belonging to base block device
    """

    pass

#==============================================================================
class LoopDevice(BlockDevice):

    #--------------------------------------------------------------------------
    def __init__(self,
            name,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            simulate = False,
            *targs,
            **kwargs
            ):
        """
        Initialisation of the base loopdevice object.

        @raise CommandNotFoundError: if some needed commands could not be found.
        @raise LoopDeviceError: on a uncoverable error.

        @param name: name of the loop device, e.g. 'loop0'
        @type name: None (if not even discoverd) or str
        @param appname: name of the current running application
        @type appname: str
        @param verbose: verbose level
        @type verbose: int
        @param version: the version string of the current object or application
        @type version: str
        @param base_dir: the base directory of all operations
        @type base_dir: str
        @param use_stderr: a flag indicating, that on handle_error() the output
                           should go to STDERR, even if logging has
                           initialized logging handlers.
        @type use_stderr: bool
        @param simulate: don't execute actions, only display them
        @type simulate: bool

        @return: None

        """

        super(LoopDevice, self).__init__(
                name = name,
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                simulate = simulate,
        )

        failed_commands = []

        self._losetup_cmd = LOSETUP_CMD
        """
        @ivar: the losetup command for manipulating the loop device
        @type: str
        """
        if not os.path.exists(self.losetup_cmd) or not os.access(
                self.losetup_cmd, os.X_OK):
            self._losetup_cmd = self.get_command('losetup')
        if not self.losetup_cmd:
            failed_commands.append('losetup')

        self._backing_file = None
        """
        @ivar: the file name of the backing file of the loop device, if it is attached
        @type: str
        """

        self._offset = None
        """
        @ivar: Loop started at offset <num> into backing file
        @type: long
        """

        self._sizelimit = None
        """
        @ivar: device limited to <num> bytes of the backing file
        @type: long
        """

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        self.initialized = True
        if self.verbose > 3:
            log.debug(_("Initialized."))

    #------------------------------------------------------------
    @property
    def losetup_cmd(self):
        """The absolute path to the OS command 'losetup'."""
        return self._losetup_cmd

    #------------------------------------------------------------
    @property
    def sysfs_loop_dir(self):
        """The directory in sysfs containing loop informations of the device."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'loop')

    #------------------------------------------------------------
    @property
    def sysfs_loop_autoclear_file(self):
        """The file in sysfs containing the flag autoclear."""
        if not self.sysfs_loop_dir:
            return None
        return os.path.join(self.sysfs_loop_dir, 'autoclear')

    #------------------------------------------------------------
    @property
    def sysfs_loop_backing_file_file(self):
        """The file in sysfs containing the backing file name."""
        if not self.sysfs_loop_dir:
            return None
        return os.path.join(self.sysfs_loop_dir, 'backing_file')

    #------------------------------------------------------------
    @property
    def sysfs_loop_offset_file(self):
        """The file in sysfs containing the offset of the device."""
        if not self.sysfs_loop_dir:
            return None
        return os.path.join(self.sysfs_loop_dir, 'offset')

    #------------------------------------------------------------
    @property
    def sysfs_loop_partscan_file(self):
        """The file in sysfs containing the flag partscan."""
        if not self.sysfs_loop_dir:
            return None
        return os.path.join(self.sysfs_loop_dir, 'partscan')

    #------------------------------------------------------------
    @property
    def sysfs_loop_sizelimit_file(self):
        """The file in sysfs containing the flag sizelimit."""
        if not self.sysfs_loop_dir:
            return None
        return os.path.join(self.sysfs_loop_dir, 'sizelimit')

    #------------------------------------------------------------
    @property
    def attached(self):
        """Is the current loop device attached to a backing file?"""
        if not self.exists:
            return False
        ldir = self.sysfs_loop_dir
        if not os.path.isdir(ldir):
            return False
        return True

    #------------------------------------------------------------
    @property
    def backing_file(self):
        """The file name of the backing file of the loop device."""
        if self._backing_file is not None:
            return self._backing_file
        if not self.attached:
            return None
        self.retr_backing_file()
        return self._backing_file

    #------------------------------------------------------------
    @property
    def offset(self):
        """The offset of the loop device in the backing file."""
        if self._offset is not None:
            return self._offset
        if not self.attached:
            return None
        self.retr_offset()
        return self._offset

    #------------------------------------------------------------
    @property
    def sizelimit(self):
        """The sizelimit of the loop device."""
        if self._sizelimit is not None:
            return self._sizelimit
        if not self.attached:
            return None
        self.retr_sizelimit()
        return self._sizelimit

    #--------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable loop device.

        @raise LoopDeviceError: if the given device name is invalid,
                                e.g. has path parts

        @param device_name: the basename of the loop device to check, e.g. 'loop0'
        @type device_name: str

        @return: the given device name is usable as a loop device name and exists.
        @rtype: bool

        """

        if not device_name:
            raise LoopDeviceError(_("No device name given."))
        if device_name != os.path.basename(device_name):
            msg  = _("Invalid device name %r given.") % (device_name)
            raise LoopDeviceError(msg)

        bd_dir = os.sep + os.path.join('sys', 'block', device_name)
        if not os.path.exists(bd_dir):
            return False

        dev_file = os.path.join(bd_dir, 'dev')
        if not os.path.exists(dev_file):
            return False
        if not os.access(dev_file, os.R_OK):
            log.warn(_("No read access to %r."), dev_file)
            return False

        handler = PbBaseHandler()
        f_content = handler.read_file(dev_file, quiet = True).strip()
        if f_content.startswith('7:'):
            return True

        return False

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(LoopDevice, self).as_dict()
        res['losetup_cmd'] = self.losetup_cmd
        res['backing_file'] = self.backing_file
        res['sysfs_loop_dir'] = self.sysfs_loop_dir
        res['sysfs_loop_autoclear_file'] = self.sysfs_loop_autoclear_file
        res['sysfs_loop_backing_file_file'] = self.sysfs_loop_backing_file_file
        res['sysfs_loop_offset_file'] = self.sysfs_loop_offset_file
        res['sysfs_loop_partscan_file'] = self.sysfs_loop_partscan_file
        res['sysfs_loop_sizelimit_file'] = self.sysfs_loop_sizelimit_file
        res['attached'] = self.attached
        res['offset'] = self.offset
        res['sizelimit'] = self.sizelimit

        return res

    #--------------------------------------------------------------------------
    def retr_backing_file(self):
        """
        A method to retrieve the backing file of the loop device

        @raise LoopDeviceError: if the backing_file file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve backing file, because it's an " +
                    "unnamed loop device object.")
            raise LoopDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve backing file of %r, because the " +
                    "loop device doesn't exists.") % (self.name)
            raise LoopDeviceError(msg)

        if not self.attached:
            msg = _("Cannot retrieve backing file of %r, because the " +
                    "loop device isn't attached.") % (self.name)
            raise LoopDeviceError(msg)

        r_file = self.sysfs_loop_backing_file_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve backing file of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve backing file of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve backing file of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        self._backing_file = f_content

    #--------------------------------------------------------------------------
    def retr_offset(self):
        """
        A method to retrieve the offset of the loop device in backing file

        @raise LoopDeviceError: if the offset file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve offset, because it's an " +
                    "unnamed loop device object.")
            raise LoopDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve offset of %r, because the " +
                    "loop device doesn't exists.") % (self.name)
            raise LoopDeviceError(msg)

        if not self.attached:
            msg = _("Cannot retrieve offset of %r, because the " +
                    "loop device isn't attached.") % (self.name)
            raise LoopDeviceError(msg)

        r_file = self.sysfs_loop_offset_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve offset of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve offset of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve offset of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        try:
            self._offset = long(f_content)
        except ValueError, e:
            msg = _("Cannot retrieve offset of %(bd)r, because " +
                    "file %(file)r has illegal content: %(err)s") % {
                    'bd': self.name, 'file': r_file, 'err': str(e)}
            raise LoopDeviceError(msg)

    #--------------------------------------------------------------------------
    def retr_sizelimit(self):
        """
        A method to retrieve the sizelimit of the loop device.

        @raise LoopDeviceError: if the sizelimit file in sysfs doesn't exists
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve sizelimit, because it's an " +
                    "unnamed loop device object.")
            raise LoopDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve sizelimit of %r, because the " +
                    "loop device doesn't exists.") % (self.name)
            raise LoopDeviceError(msg)

        if not self.attached:
            msg = _("Cannot retrieve sizelimit of %r, because the " +
                    "loop device isn't attached.") % (self.name)
            raise LoopDeviceError(msg)

        r_file = self.sysfs_loop_sizelimit_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve sizelimit of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve sizelimit of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve sizelimit of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise LoopDeviceError(msg)

        try:
            self._sizelimit = long(f_content)
        except ValueError, e:
            msg = _("Cannot retrieve sizelimit of %(bd)r, because " +
                    "file %(file)r has illegal content: %(err)s") % {
                    'bd': self.name, 'file': r_file, 'err': str(e)}
            raise LoopDeviceError(msg)

    #--------------------------------------------------------------------------
    def attach(self, filename, sudo = None, offset = None, sizelimit = None):
        """
        Attach the current loop device object to the given file.

        The current loop device object may not attached before. The file of
        the given filename must exists before and must be a regular file.

        @raise LoopDeviceError: if the requirements are not fulfilled or the
                                call of 'losetup' was not successful.

        @param filename: the backing filename to attach to the current
                         loop device object
        @type filename: str
        @param sudo: execute losetup with sudo as root
        @type sudo: bool or None
        @param offset: the offset in bytes, where the data starts in the
                       backing file
        @type offset: long or None
        @param sizelimit: the limit in bytes to use from the backing file
        @type sizelimit: long or None

        """

        if self.name and self.attached:
            msg = _("The current loop device %(lo)r is even attached to the " +
                    "backing file %(bfile)r.") % {'lo': self.device,
                    'bfile': self.backing_file}
            raise LoopDeviceError(msg)

        if not filename:
            msg = _("No filename given onn calling attach().")
            raise LoopDeviceError(msg)

        filename = str(filename)

        if not os.path.exists(filename):
            msg = _("File %r doesn't exists.") % (filename)
            raise LoopDeviceError(msg)

        if not os.path.isfile(filename):
            msg = _("File %r exists, but is not a regular file.") % (filename)
            raise LoopDeviceError(msg)

        if self.name:
            log.info("Attaching %r to loop device %s ...", filename, self.device)
        else:
            log.info("Attaching %r to a loop device ...", filename)

        if offset is not None:
            offset = long(offset)

        if sizelimit is not None:
            sizelimit = long(sizelimit)

        cmd = [self.losetup_cmd]

        if offset is not None:
            cmd.append('--offset')
            cmd.append('%d' % (offset))

        if sizelimit is not None:
            cmd.append('--sizelimit')
            cmd.append('%d' % (sizelimit))

        if self.name:
            cmd.append(self.device)
        else:
            cmd.append('--find')
            cmd.append('--show')

        cmd.append(filename)

        cmdline = ' '.join(cmd)
        (ret_code, std_out, std_err) = self.call(cmd, sudo = sudo)

        if ret_code:
            err = _('undefined error')
            if std_err:
                e = std_err.replace('\n', ' ').strip()
                if e:
                    err = e
            msg = _("Error %d on attaching %r with losetup: %s") % (
                    ret_code, filename, err)
            raise LoopDeviceError(msg)

        if not self.name:
            log.debug("Trying to get the new device name from %r ...", std_out)
            dev = std_out.strip()
            match = re.match(r'^(?:/dev/)?([^/]+)', dev)
            if not match:
                msg = _("Somehow I could not retrieve the new loop device " +
                        "name from %r.") % (dev)
                raise LoopDeviceError(msg)
            self.name = match.group(1)
            log.info("Used loop device for attaching: %r", self.device)
            if not self.exists:
                msg = _("Got %(lo)r as a new loop device name, but %(dir)s " +
                        "doesn't seems to exist.") % {'lo': self.name,
                        'dir': self.sysfs_bd_dir}
                raise LoopDeviceError(msg)

        if not self.attached:
            msg = _("Loop device %(lo)r was attached to %(file)r, but " +
                    "%(dir)s doesn't seems to exist.") % {'lo': self.name,
                   'file': filename, 'dir': self.sysfs_loop_dir}
            raise LoopDeviceError(msg)

        self.retr_backing_file()

    #--------------------------------------------------------------------------
    def detach(self, sudo = None):
        """
        Detaches the current loop device from the backing file
        with "losetup --detach".

        @raise LoopDeviceError: if the call of 'losetup' was not successful.

        @param sudo: execute losetup with sudo as root
        @type sudo: bool or None

        """

        if not self.attached:
            log.warn(_("Device %r is even detached from some backing file."),
                    self.device)
            self._backing_file = None
            self._offset = None
            self._sizelimit = None
            return

        log.info("Detaching loop device %s ...", self.device)

        cmd = [
                self.losetup_cmd,
                '--detach',
                self.device
        ]

        cmdline = ' '.join(cmd)
        (ret_code, std_out, std_err) = self.call(cmd, sudo = sudo)

        if ret_code:
            err = _('undefined error')
            if std_err:
                e = std_err.replace('\n', ' ').strip()
                if e:
                    err = e
            msg = _("Error %d on detaching %r with losetup: %s") % (
                    ret_code, self.device, err)
            raise LoopDeviceError(msg)

        self._backing_file = None
        self._offset = None
        self._sizelimit = None

        return

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
