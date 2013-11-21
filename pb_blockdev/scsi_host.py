#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the ScsiHost class
"""

# Standard modules
import sys
import os
import logging
import re
import glob

# Third party modules

# Own modules
import pb_base
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust
from pb_base.common import caller_search_path

from pb_base.errors import PbError

from pb_base.object import PbBaseObjectError

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_blockdev.hbtl import HBTLError
from pb_blockdev.hbtl import HBTL

from pb_blockdev.translate import translator

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.8.0'

log = logging.getLogger(__name__)

# /sys/class/scsi_host
base_sysfs_scsihost_dir = os.sep + os.path.join('sys', 'class', 'scsi_host')

# /sys/bus/scsi/devices
base_sysfs_scsi_devices_dir = os.sep + os.path.join('sys', 'bus', 'scsi', 'devices')

re_hostid = re.compile(r'/host(\d+)$')
re_hbtl = re.compile(r'^\d+:(\d+):(\d+):(\d+)$')

#==============================================================================
class ScsiHostError(PbBaseObjectError):
    """Base error class for all stuff belonging to this module."""
    pass

#==============================================================================
class ScsiHost(PbBaseHandler):
    """
    Encapsulation class for SCSI hosts.
    """

    #------------------------------------------------------------
    def __init__(self,
            host_id,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            simulate = False,
            sudo = False,
            *targs,
            **kwargs
            ):
        """
        Initialisation of the ScsiHost object.

        @param host_id: the numeric SCSI host Id
        @type host_id: int
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
        @param sudo: should the command executed by sudo by default
        @type sudo: bool

        @return: None

        """

        self._host_id = int(host_id)
        """
        @ivar: The numeric SCSI host Id
        @type: int
        """

        self._active_mode = None
        self._proc_name = None
        self._state = None

        self.luns = []
        """
        @ivar: all found LUN devices of this SCSI host.
        @type: list of tuple, where all tuples have three integer members:
                * bus Id
                * target Id
                * LUN Id
        """

        super(ScsiHost, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
                simulate = simulate,
                sudo = sudo,
                *targs, **kwargs
        )

        self.init_lun_list()

        self.initialized = True

    #------------------------------------------------------------
    @property
    def host_id(self):
        """The numeric SCSI host Id."""
        return self._host_id

    #------------------------------------------------------------
    @property
    def hostname(self):
        """The name of the SCSI host, e.g. 'host1'."""
        return "host%d" % (self.host_id)

    #------------------------------------------------------------
    @property
    def sysfs_dir(self):
        """
        The apropriate directory under /sys/class/scsi_host,
        e.g. '/sys/class/scsi_host/host2'
        """
        return os.path.join(base_sysfs_scsihost_dir, self.hostname)

    #------------------------------------------------------------
    @property
    def sysfs_dir_real(self):
        """The real path of the scsi_host dir in sysfs"""
        if not self.sysfs_dir:
            return None
        if not os.path.exists(self.sysfs_dir):
            return None
        return os.path.realpath(self.sysfs_dir)

    #------------------------------------------------------------
    @property
    def exists(self):
        """Does the current scsi_host really exists?"""
        if not self.sysfs_dir:
            return False
        return os.path.exists(self.sysfs_dir)

    #------------------------------------------------------------
    @property
    def active_mode_file(self):
        """The file containing the active mode."""
        return os.path.join(self.sysfs_dir, 'active_mode')

    #------------------------------------------------------------
    @property
    def active_mode(self):
        """The active mode of the current SCSI host."""
        if self._active_mode is not None:
            return self._active_mode
        if not self.exists:
            return None
        self._active_mode = self.retr_active_mode()
        return self._active_mode

    #------------------------------------------------------------
    @property
    def proc_name_file(self):
        """The file containing the name of the owning process."""
        return os.path.join(self.sysfs_dir, 'proc_name')

    #------------------------------------------------------------
    @property
    def proc_name(self):
        """The name of the owning process of the current SCSI host."""
        if self._proc_name is not None:
            return self._proc_name
        if not self.exists:
            return None
        self._proc_name = self.retr_proc_name()
        return self._proc_name

    #------------------------------------------------------------
    @property
    def scan_file(self):
        """The file used for scanning the SCSI host."""
        return os.path.join(self.sysfs_dir, 'scan')

    #------------------------------------------------------------
    @property
    def state_file(self):
        """The file containing the state of the current SCSI host."""
        return os.path.join(self.sysfs_dir, 'state')

    #------------------------------------------------------------
    @property
    def state(self):
        """The current state of the current SCSI host."""
        if self._state is not None:
            return self._state
        if not self.exists:
            return None
        self._state = self.retr_state()
        return self._state

    #------------------------------------------------------------
    @property
    def device_dir(self):
        """The 'device directory under the main sysf dir."""
        return os.path.join(self.sysfs_dir, 'device')

    #------------------------------------------------------------
    @property
    def device_dir_real(self):
        """The real path of the device dir in sysfs"""
        if not self.device_dir:
            return None
        if not os.path.exists(self.device_dir):
            return None
        return os.path.realpath(self.device_dir)

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(ScsiHost, self).as_dict(short = short)
        res['host_id'] = self.host_id
        res['hostname'] = self.hostname
        res['exists'] = self.exists
        res['sysfs_dir'] = self.sysfs_dir
        res['sysfs_dir_real'] = self.sysfs_dir_real
        res['active_mode_file'] = self.active_mode_file
        res['active_mode'] = self.active_mode
        res['proc_name_file'] = self.proc_name_file
        res['proc_name'] = self.proc_name
        res['scan_file'] = self.scan_file
        res['state_file'] = self.state_file
        res['state'] = self.state
        res['device_dir'] = self.device_dir
        res['device_dir_real'] = self.device_dir_real

        res['luns'] = []
        for hbtl in self.luns:
            res['luns'].append(str(hbtl))

        return res

    #--------------------------------------------------------------------------
    def __cmp__(self, other):
        """
        Operator overloading for the comparision function, which is implicitely
        used with the sorted function.
        """

        if not isinstance(other, ScsiHost):
            msg = _("Comparision partner %r is not a ScsiHost object.") % (other)
            raise ValueError(msg)

        return cmp(self.host_id, other.host_id)

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("host_id=%r" % (self.host_id))
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("version=%r" % (self.version))
        fields.append("base_dir=%r" % (self.base_dir))
        fields.append("use_stderr=%r" % (self.use_stderr))
        fields.append("initialized=%r" % (self.initialized))

        out += ", ".join(fields) + ")>"
        return out

    #--------------------------------------------------------------------------
    def retr_active_mode(self):
        """Retrieving the current content of the active_mode_file."""

        if not self.exists:
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'active_mode', 'of': self.hostname,
                    'target': self.sysfs_dir}
            raise ScsiHostError(msg)
        if not os.path.exists(self.active_mode_file):
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'active_mode', 'of': self.hostname,
                    'target': self.active_mode_file}
            raise ScsiHostError(msg)
        if not os.access(self.active_mode_file, os.R_OK):
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r is not readable.") % {
                    'what': 'active_mode', 'of': self.hostname,
                    'target': self.active_mode_file}
            raise ScsiHostError(msg)

        return self.read_file(self.active_mode_file, quiet = True).strip()

    #--------------------------------------------------------------------------
    def retr_proc_name(self):
        """Retrieving the current content of the proc_name_file."""

        if not self.exists:
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'proc_name', 'of': self.hostname,
                    'target': self.sysfs_dir}
            raise ScsiHostError(msg)
        if not os.path.exists(self.proc_name_file):
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'proc_name', 'of': self.hostname,
                    'target': self.proc_name_file}
            raise ScsiHostError(msg)
        if not os.access(self.proc_name_file, os.R_OK):
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r is not readable.") % {
                    'what': 'proc_name', 'of': self.hostname,
                    'target': self.proc_name_file}
            raise ScsiHostError(msg)

        return self.read_file(self.proc_name_file, quiet = True).strip()

    #--------------------------------------------------------------------------
    def retr_state(self):
        """Retrieving the current content of the state_file."""

        if not self.exists:
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': _('state'), 'of': self.hostname,
                    'target': self.sysfs_dir}
            raise ScsiHostError(msg)
        if not os.path.exists(self.state_file):
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': _('state'), 'of': self.hostname,
                    'target': self.state_file}
            raise ScsiHostError(msg)
        if not os.access(self.state_file, os.R_OK):
            msg = _("Cannot retrieve %(what)s of %(of)r, %(target)r is not readable.") % {
                    'what': _('state'), 'of': self.hostname,
                    'target': self.state_file}
            raise ScsiHostError(msg)

        return self.read_file(self.state_file, quiet = True).strip()

    #--------------------------------------------------------------------------
    def init_lun_list(self):
        """
        Initializes the list self.luns with all found luns
        of this SCSI host.
        """

        self.luns = []
        if not os.path.exists(self.device_dir):
            return

        unsorted_luns = []

        pattern = os.path.join(base_sysfs_scsi_devices_dir,
                ('%d:[0-9]*:[0-9]*:[0-9]*' % (self.host_id)))

        if self.verbose > 2:
            log.debug(_("Search pattern for LUNs: %r ..."), pattern)
        lun_dirs = glob.glob(pattern)

        for lun_dir in lun_dirs:

            if self.verbose > 3:
                log.debug(_("Checking LUN directory %r ..."), lun_dir)
            hbtl_str = os.path.basename(lun_dir)
            try:
                hbtl = HBTL.from_string(hbtl_str)
            except ValueError, e:
                if self.verbose > 2:
                    log.warn(_("%r is not a valid HBTL address: %s"), hbtl_str, e)
                continue
            unsorted_luns.append(hbtl)

        self.luns = sorted(unsorted_luns)

    #--------------------------------------------------------------------------
    def target_dir(self, bus_id, target_id):
        """
        Returns the directory of the given target beyond the scsi_host
        directory in sysfs, e.g.::
            /sys/class/scsi_host/host0/device/target0:0:8
        """

        t1 = "target%d:%d:%d" % (self.host_id, bus_id, target_id)
        return os.path.join(base_sysfs_scsi_devices_dir, t1)

    #--------------------------------------------------------------------------
    def lun_dir(self, bus_id, target_id, lun_id):
        """
        Returns the directory of the given LUN beyond the scsi_host
        directory in sysfs, e.g.::
            /sys/class/scsi_host/host0/device/target0:0:8/0:0:8:0
        """

        t2 = "%d:%d:%d:%d" % (self.host_id, bus_id, target_id, lun_id)
        return os.path.join(base_sysfs_scsi_devices_dir, t2)

    #--------------------------------------------------------------------------
    def lun_block_dir(self, bus_id, target_id, lun_id):
        """
        Returns the block directory of the given LUN beyond the scsi_host
        directory in sysfs, e.g.::
            /sys/class/scsi_host/host0/device/target0:0:8/0:0:8:0/block
        """
        ldir = self.lun_dir(bus_id, target_id, lun_id)
        return os.path.join(ldir, 'block')

    #--------------------------------------------------------------------------
    def lun_blockdevice(self, bus_id, target_id, lun_id):
        """
        Returns the name of the appropriate blockdevice, if there is such
        one existing, else None is returning.
        """

        bdir = self.lun_block_dir(bus_id, target_id, lun_id)
        if not os.path.exists(bdir):
            return None

        pattern = os.path.join(bdir, '*')
        files = glob.glob(pattern)
        if self.verbose > 3:
            log.debug(_("Found blockdevice dirs: %s"), pp(files))
        if not files:
            return None

        bdevdir = files[0]
        bdevname = os.path.basename(bdevdir)
        if self.verbose > 3:
            msg = _("Found blockdevice %(bd)r for '%(h)d:%(b)d:%(t)d:%(l)d'.") % {
                    'bd': bdevname, 'h': self.host_id,
                    'b': bus_id, 't': target_id, 'l': lun_id}
            log.debug(msg)

        return bdevname

#==============================================================================
def get_scsi_hosts(
        appname = None,
        verbose = 0,
        base_dir = None,
        use_stderr = False,
        simulate = False,
        sudo = False,
        *targs,
        **kwargs
        ):
    """
    Returns a list of all available SCSI hosts on this machine.
    """

    pattern = os.path.join(base_sysfs_scsihost_dir, 'host*')
    if verbose > 2:
        log.debug(_("Searching for SCSI hosts with pattern %r ..."), pattern)

    dirs = glob.glob(pattern)
    result = []

    for host_dir in dirs:
        match = re_hostid.search(host_dir)
        if not match:
            log.warn(_("Invalid scsi_host directory %r found."), host_dir)
            continue
        host_id = int(match.group(1))
        scsi_host = ScsiHost(
                host_id,
                appname = appname,
                verbose = verbose,
                base_dir = base_dir,
                use_stderr = use_stderr,
                simulate = simulate,
                sudo = sudo,
                *targs, **kwargs
        )
        result.append(scsi_host)

    return sorted(result)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
