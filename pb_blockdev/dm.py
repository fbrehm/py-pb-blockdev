#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a devicemapper device class
"""

# Standard modules
import sys
import os
import logging
import re
import glob
import time
import uuid

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

__version__ = '0.3.3'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

DMSETUP_CMD = os.sep + os.path.join('sbin', 'dmsetup')

base_dev_mapper_dir = os.sep + os.path.join('dev', 'mapper')

#==============================================================================
class DmDeviceError(BlockDeviceError):
    """
    Base error class for all exceptions belonging to devicemapper device
    """

    pass

#==============================================================================
class DmDeviceInitError(DmDeviceError):
    """
    Error class for exceptions happening on initialisation of
    a DeviceMapperDevice object.
    """

    pass

#==============================================================================
class DmSuspendError(DmDeviceError):
    """
    Error class for a failure in suspending a DM device.
    """

    #------------------------------------------------------------------------
    def __init__(self, dm_name, ret_code, err_msg):
        """
        Constructor.

        @param dm_name: the device mapper name
        @type dm_name: str
        @param ret_code: the shell return code from "dmsetup suspend ..."
        @type ret_code: int
        @param err_msg: the error message from "dmsetup suspend ..."
        @type err_msg: str

        """

        self.dm_name = dm_name
        self.ret_code = ret_code
        self.err_msg = err_msg

    #------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting of object into a string
        """

        msg = _("Error %(errno)d suspending device mapper device %(dev)r: %(msg)s")
        return msg % {'errno': self.ret_code, 'dev': self.dm_name,
                'msg': self.err_msg}

#==============================================================================
class DmResumeError(DmDeviceError):
    """
    Error class for a failure in resuming a DM device.
    """

    #------------------------------------------------------------------------
    def __init__(self, dm_name, ret_code, err_msg):
        """
        Constructor.

        @param dm_name: the device mapper name
        @type dm_name: str
        @param ret_code: the shell return code from "dmsetup resume ..."
        @type ret_code: int
        @param err_msg: the error message from "dmsetup resume ..."
        @type err_msg: str

        """

        self.dm_name = dm_name
        self.ret_code = ret_code
        self.err_msg = err_msg

    #------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting of object into a string
        """

        msg = _("Error %(errno)d resuming device mapper device %(dev)r: %(msg)s")
        return msg % {'errno': self.ret_code, 'dev': self.dm_name, 'msg': self.err_msg}

#==============================================================================
class DmTableGetError(DmDeviceError):
    """
    Error class for getting a device mapper table.
    """

    #------------------------------------------------------------------------
    def __init__(self, dm_name, ret_code, err_msg):
        """
        Constructor.

        @param dm_name: the device mapper name
        @type dm_name: str
        @param ret_code: the shell return code from "dmsetup table ..."
        @type ret_code: int
        @param err_msg: the error message from "dmsetup table ..."
        @type err_msg: str

        """

        self.ret_code = ret_code
        self.dm_name = dm_name
        self.err_msg = err_msg

    #------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting of object into a string
        """

        msg = _("Error %(errno)d getting device mapper table of device %(dev)r: %(msg)s")
        return msg % {'errno': self.ret_code, 'dev': self.dm_name, 'msg': self.err_msg}

#==============================================================================
class DmTableSetError(DmDeviceError):
    """
    Error class for setting a device mapper table.
    """

    #------------------------------------------------------------------------
    def __init__(self, dm_name, ret_code, table, err_msg):
        """
        Constructor.

        @param dm_name: the device mapper name
        @type dm_name: str
        @param ret_code: the shell return code from "dmsetup table ..."
        @type ret_code: int
        @param table: the new table, that should be set
        @type table: str
        @param err_msg: the error message from "dmsetup table ..."
        @type err_msg: str

        """

        self.ret_code = ret_code
        self.dm_name = dm_name
        self.table = table
        self.err_msg = err_msg

    #------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting of object into a string
        """

        msg = _("Error %(errno)d setting device mapper table %(tbl)r of device %(dev)r: %(msg)s")
        return msg % {'errno': self.ret_code, 'tbl': self.table,
                'dev': self.dm_name, 'msg': self.err_msg}

#==============================================================================
class DmRemoveError(DmDeviceError):
    """
    Error class for catching errors on removing a devicemapper device.
    """

    #------------------------------------------------------------------------
    def __init__(self, dm_name, err_msg = None):
        """
        Constructor.

        @param dm_name: the device mapper name
        @type dm_name: str
        @param err_msg: the error message from "dmsetup remove ..."
        @type err_msg: str
        """

        self.dm_name = dm_name
        self.err_msg = None
        if err_msg is None:
            self.err_msg = ''
        else:
            self.err_msg = str(err_msg)
        self.err_msg = self.err_msg.strip()

        if not self.err_msg:
            self.err_msg = _("Unknown error")

    #------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting of object into a string.
        """

        return _("Error removing device mapper device %(dev)r: %(msg)s") % {
                'dev': self.dm_name, 'msg': self.err_msg}

#==============================================================================
class DmCreationError(DmDeviceError):
    """
    Error class for catching errors on creating a devicemapper device.
    """

    #------------------------------------------------------------------------
    def __init__(self, dm_name, err_msg = None):
        """
        Constructor.

        @param dm_name: the device mapper name
        @type dm_name: str
        @param err_msg: the error message from "dmsetup create ..."
        @type err_msg: str
        """

        self.dm_name = dm_name
        self.err_msg = None
        if err_msg is None:
            self.err_msg = ''
        else:
            self.err_msg = str(err_msg)
        self.err_msg = self.err_msg.strip()

        if not self.err_msg:
            self.err_msg = _("Unknown error")

    #------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting of object into a string.
        """

        return _("Error creating device mapper device %(dev)r: %(msg)s") % {
                'dev': self.dm_name, 'msg': self.err_msg}

#==============================================================================
class DeviceMapperDevice(BlockDevice):

    #--------------------------------------------------------------------------
    def __init__(self,
            name = None,
            dm_name = None,
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
        Initialisation of the devicemapper device object.

        One of parameters 'name' or 'dm_name' must be given to initialize
        the object.

        @raise CommandNotFoundError: if some needed commands could not be found.
        @raise DmDeviceInitError: on a uncoverable error.

        @param name: name of the loop device, e.g. 'dm-1'
        @type name: None (if not even discoverd) or str
        @param dm_name: the devicemapper name
        @type dm_name: str or None
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

        # Normalisation of 'name' and 'dm_name'
        if name is not None:
            name = str(name).strip()

        if dm_name is not None:
            dm_name = str(dm_name).strip()

        # One of those two parameters must be valid:
        if not name and not dm_name:
            msg = _("In minimum one parameter of 'name' and 'dm_name' must be given on initialisation of a DeviceMapperObject.")
            raise DmDeviceInitError(msg)

        super(DeviceMapperDevice, self).__init__(
                name = name,
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                simulate = simulate,
        )
        self.initialized = False

        if not name:
            name = self.retr_blockdev_name(dm_name)
            self._name = name

        self._dm_name = dm_name
        """
        @ivar: the devicemapper name of the device
        @type: str
        """

        failed_commands = []

        self._dmsetup_cmd = DMSETUP_CMD
        """
        @ivar: the dmsetup command for manipulating the devicemapper device
        @type: str
        """
        if not os.path.exists(self.dmsetup_cmd) or not os.access(
                self.dmsetup_cmd, os.X_OK):
            self._dmsetup_cmd = self.get_command('dmsetup')
        if not self.dmsetup_cmd:
            failed_commands.append('dmsetup')

        self._suspended = None
        """
        @ivar: flag that the current device is in suspended mode
        @type: bool or None
        """

        self._uuid = None
        """
        @ivar: the devicemapper UUID
        @type: str or None
        """

        self._table = None
        """
        @ivar: the device mapper table (whatever it is)
        @type: str
        """

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        self.initialized = True
        if self.verbose > 3:
            log.debug(_("Initialized."))

    #------------------------------------------------------------
    @property
    def dmsetup_cmd(self):
        """The absolute path to the OS command 'dmsetup'."""
        return self._dmsetup_cmd

    #------------------------------------------------------------
    @property
    def sysfs_dm_dir(self):
        """
        The directory in sysfs containing devicemapper
        informations of the device.
        """
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'dm')

    #------------------------------------------------------------
    @property
    def sysfs_dm_name_file(self):
        """The file in sysfs containing the devicemapper name of the device."""
        if not self.sysfs_dm_dir:
            return None
        return os.path.join(self.sysfs_dm_dir, 'name')

    #------------------------------------------------------------
    @property
    def sysfs_suspended_file(self):
        """The file in sysfs containing, whether the device is suspended."""
        if not self.sysfs_dm_dir:
            return None
        return os.path.join(self.sysfs_dm_dir, 'suspended')

    #------------------------------------------------------------
    @property
    def sysfs_uuid_file(self):
        """The file in sysfs containing the devicemapper uuid of the device."""
        if not self.sysfs_dm_dir:
            return None
        return os.path.join(self.sysfs_dm_dir, 'uuid')

    #------------------------------------------------------------
    @property
    def dm_name(self):
        """The devicemapper name of the device."""
        if self._dm_name is not None:
            return self._dm_name
        if not self.exists:
            return None
        if not os.path.exists(self.sysfs_dm_name_file):
            return None
        self.retr_dm_name()
        return self._dm_name

    #------------------------------------------------------------
    @property
    def suspended(self):
        """A flag, whether the device is suspended."""
        if self._suspended is not None:
            return self._suspended
        if not self.exists:
            return None
        self.retr_suspended()
        return self._suspended

    #------------------------------------------------------------
    @property
    def uuid(self):
        """The UUID of the devicemapper device.."""
        if self._uuid is not None:
            return self._uuid
        if not self.exists:
            return None
        self.retr_uuid()
        return self._uuid

    #------------------------------------------------------------
    @property
    def table(self):
        """The device mapper table (whatever it is)."""
        if not self.exists:
            return None
        return self._get_table()

    #--------------------------------------------------------------------------
    @staticmethod
    def isa(device_name):
        """
        Returns, whether the given device name is a usable devicemapper device.

        @raise DmDeviceError: if the given device name is invalid,
                              e.g. has path parts

        @param device_name: the basename of the loop device to check, e.g. 'dm-1'
        @type device_name: str

        @return: the given device name is usable as a devicemapper device name
                 and exists.
        @rtype: bool

        """

        if not device_name:
            raise DmDeviceError(_("No device name given."))
        if device_name != os.path.basename(device_name):
            msg  = _("Invalid device name %r given.") % (device_name)
            raise DmDeviceError(msg)

        bd_dir = os.sep + os.path.join('sys', 'block', device_name)
        if not os.path.exists(bd_dir):
            return False

        dm_dir = os.path.join(bd_dir, 'dm')
        if not os.path.exists(dm_dir):
            return False

        return True

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(DeviceMapperDevice, self).as_dict(short = short)
        res['dmsetup_cmd'] = self.dmsetup_cmd
        res['sysfs_dm_dir'] = self.sysfs_dm_dir
        res['sysfs_dm_name_file'] = self.sysfs_dm_name_file
        res['sysfs_suspended_file'] = self.sysfs_suspended_file
        res['sysfs_uuid_file'] = self.sysfs_uuid_file
        res['dm_name'] = self.dm_name
        res['suspended'] = self.suspended
        res['uuid'] = self.uuid
        res['table'] = self.table

        return res

    #--------------------------------------------------------------------------
    def retr_blockdev_name(self, dm_name):
        """
        A method to retrieve the blockdevice name from the device mapper name

        @param dm_name: the device mapper name to look for.
        @type dm_name: str

        @return: the blockdevice name
        @rtype: str

        """

        if not os.path.isdir(base_dev_mapper_dir):
            if self.verbose > 3:
                log.debug(_("Base device dir of device mapper %r doesn't exists."),
                        base_dev_mapper_dir)
            return None

        pattern = os.path.join(base_sysfs_blockdev_dir, 'dm-*', 'dm', 'name')
        name_files = glob.glob(pattern)

        re_bd_name = re.compile(r'^.*/(dm-\d+)/dm/name$')

        for name_file in name_files:

            bd_name = None
            match = re_bd_name.search(name_file)
            if match:
                bd_name = match.group(1)
            else:
                log.warn(_("Could not extract blockdevice name from %r."),
                        name_file)
                continue
            if self.verbose > 3:
                log.debug(_("Checking blockdevice %r for DM name ..."), bd_name)

            if not os.access(name_file, os.R_OK):
                msg = _("Cannot retrieve name from of %r, because of no read access.") % (
                        name_file)
                raise DmDeviceError(msg)

            f_content = self.read_file(name_file, quiet = True).strip()
            if not f_content:
                msg = _("Cannot retrieve name from %r, because file has no content.") % (
                        name_file)
                raise DmDeviceError(msg)

            if f_content == dm_name:
                return bd_name

        if self.verbose > 2:
            log.debug(_("Could not retrieve blockdevice name for DM name %r."),
                    dm_name)

        return None

    #--------------------------------------------------------------------------
    def retr_dm_name(self):
        """
        A method to retrieve the devicemapper name of the device

        @raise DmDeviceError: if the devicemapper name file in sysfs doesn't
                              exists or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve dm_name file, because it's an unnamed devicemapper device object.")
            raise DmDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve dm_name file of %r, because the devicemapper device doesn't exists.") % (
                    self.name)
            raise DmDeviceError(msg)

        r_file = self.sysfs_dm_name_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve dm_name file of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve dm_name file of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve dm_name file of %(bd)r, because file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        self._dm_name = f_content

    #--------------------------------------------------------------------------
    def retr_suspended(self):
        """
        A method to retrieve whether the device is in suspended mode.

        @raise DmDeviceError: if the suspended file in sysfs doesn't exists
                              or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve suspended state, because it's an unnamed devicemapper device object.")
            raise DmDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve suspended state of %r, because the devicemapper device doesn't exists.") % (
                    self.name)
            raise DmDeviceError(msg)

        r_file = self.sysfs_suspended_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve suspended state of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve suspended state of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve suspended state of %(bd)r, because file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        if f_content == '1':
            self._suspended = True
        else:
            self._suspended = False

    #--------------------------------------------------------------------------
    def retr_uuid(self):
        """
        A method to retrieve the UUID of the current devicemapper device

        @raise DmDeviceError: if the uuid file in sysfs doesn't exists
                              or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve UUID, because it's an unnamed devicemapper device object.")
            raise DmDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve UUID of %r, because the devicemapper device doesn't exists.") % (
                    self.name)
            raise DmDeviceError(msg)

        r_file = self.sysfs_uuid_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve UUID of %(bd)r, because the file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve UUID of %(bd)r, because no read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise DmDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()

        self._uuid = f_content

    #--------------------------------------------------------------------------
    def _get_table(self, force = False):
        """
        Tries to get the current device mapper table. If not found in
        self._table it calls "dmsetup table <dmname>" to retrieve the current
        dm table (and save it in self._table).

        @raise DmTableGetError: on some errors.

        @param force: tries allways to get the current information
                      with "dmsetup table ...", independend of content
                      of self._table.
        @type force: bool

        @return: the current device mapper table.
        @rtype: str

        """

        if self._table and not force:
            return self._table

        if not self.dm_name:
            log.debug(_("Cannot retrieve DM table, because I have no name."))
            return None

        if self.verbose > 1:
            log.debug(_("Trying to get current device mapper table of %r ..."),
                    self.dm_name)

        cmd = [self.dmsetup_cmd, 'table', self.dm_name]
        (ret_code, std_out, std_err) = self.call(
                cmd,
                quiet = True,
                sudo = True,
                simulate = False
        )
        if ret_code:
            raise DmTableGetError(self.dm_name, ret_code, std_err)

        table = std_out.strip()
        if table == '':
            log.warn(_("Device %r has an empty DM table."), self.dm_name)

        self._table = table
        return table

    #--------------------------------------------------------------------------
    def suspend(self):
        """
        Suspends the appropriate DM device.

        @raise DmSuspendError: on some errors.

        @return: None

        """

        log.info(_("Suspending DM device %r ..."), self.dm_name)
        cmd = [self.dmsetup_cmd, 'suspend', self.dm_name]
        start_time = time.time()
        (ret_code, std_out, std_err) = self.call(cmd, quiet = True, sudo = True)
        if ret_code:
            raise DmSuspendError(self.dm_name, ret_code, std_err)

        if self.simulate:
            return

        self.retr_suspended()
        if not self.suspended:
            i = 0
            while i < 10:
                log.debug(_("DM device %r is not suspended yet, but it should so. Waiting a minimal time ..."),
                        self.dm_name)
                time.sleep(0.2)
                self.retr_suspended()
                if self.suspended:
                    break
                i += 1

            if not self.suspended:
                msg = _("not suspended after %0.3f seconds, but it should so") % (
                        start_time - time.time())
                raise DmSuspendError(self.dm_name, 99, msg)

        log.debug(_("DM device %(dev)r suspended in %(sec)0.3f seconds.") % {
                'dev': self.dm_name, 'sec': (start_time - time.time())})

    #--------------------------------------------------------------------------
    def resume(self):
        """
        Resumes the appropriate DM device.

        @raise DmResumeError: on some errors.

        @return: None

        """

        log.info(_("Resuming DM device %r ..."), self.dm_name)
        cmd = [self.dmsetup_cmd, 'resume', self.dm_name]
        start_time = time.time()
        (ret_code, std_out, std_err) = self.call(cmd, quiet = True, sudo = True)
        if ret_code:
            raise DmResumeError(self.dm_name, ret_code, std_err)

        if self.simulate:
            return

        self.retr_suspended()
        if self.suspended:
            i = 0
            while i < 10:
                log.debug(_("DM device %r is not resumed yet, but it should so. Waiting a minimal time ..."),
                        self.dm_name)
                time.sleep(0.2)
                self.retr_suspended()
                if not self.suspended:
                    break
                i += 1

            if self.suspended:
                msg = _("not resumed after %0.3f seconds, but it should so") % (
                        start_time - time.time())
                raise DmResumeError(self.dm_name, 99, msg)

        log.debug(_("DM device %(dev)r resumed in %(sec)0.3f seconds.") % {
                'dev': self.dm_name, 'sec': (start_time - time.time())})

    #--------------------------------------------------------------------------
    def remove(self, force = False):
        """
        Removing the devicemapper device independend of holder and slave
        device.

        @param force: Execute a forced removing of the device.
        @type force: bool

        @raise DmSuspendError: if the device couldn't suspended before.
        @raise DmRemoveError: on some other errors.

        """

        if not self.suspended:
            try:
                self.suspend()
            except DmSuspendError, e:
                if force:
                    log.error(str(e))
                    log.info(_("Force switch is set, trying to remove device mapper device %r anyhow ..."),
                            self.dm_name)
                else:
                    raise

        cmd = [self.dmsetup_cmd, 'remove']
        if force:
            cmd.append('--force')
        cmd.append(self.dm_name)

        if force:
            log.info(_("Removing devicemapper device %r FORCED ..."),
                    self.dm_name)
        else:
            log.info(_("Removing devicemapper device %r ..."), self.dm_name)

        start_time = time.time()
        (ret_code, std_out, std_err) = self.caller(
                cmd,
                quiet = True,
                force = True,
                sudo = True
        )
        if ret_code:
            msg = (_("error %d: ") % (ret_code)) + std_err
            raise DmRemoveError(self.dm_name, msg)

        if self.simulate:
            return

        if self.exists:
            i = 0
            while i < 10:
                log.debug(_("DM device %r is not removed yet, but it should so. Waiting a minimal time ..."),
                        self.dm_name)
                time.sleep(0.2)
                if not self.exists:
                    break
                i += 1

            if self.exists:
                msg = _("not removed after %0.1f seconds, but it should so") % (
                        start_time - time.time())
                raise DmRemoveError(self.dm_name, msg)

        log.debug(_("DM device %(dev)r removed in %(sec)0.3f seconds.") + {
                'dev': self.dm_name, 'sec': (start_time - time.time())})

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
