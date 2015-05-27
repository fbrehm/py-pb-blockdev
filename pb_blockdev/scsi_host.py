#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the ScsiHost class
"""

# Standard modules
import os
import logging
import re
import glob
import time

# Third party modules

# Own modules
from pb_base.common import pp

from pb_base.object import PbBaseObjectError

from pb_base.handler import PbBaseHandler

from pb_blockdev.hbtl import HBTL

from pb_blockdev.scsi import ScsiDevice

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.10.3'

LOG = logging.getLogger(__name__)

# /sys/class/scsi_host
BASE_SYSFS_SCSIHOST_DIR = os.sep + os.path.join('sys', 'class', 'scsi_host')

# /sys/bus/scsi/devices
BASE_SYSFS_SCSI_DEVICES_DIR = os.sep + os.path.join('sys', 'bus', 'scsi', 'devices')

# Default waiting time in seconds after scanning for a HBTL for
# appearing the nawe device
DEFAULT_WAIT_ON_SCAN = 5.1

RE_HOSTID = re.compile(r'/host(\d+)$')


# =============================================================================
class ScsiHostError(PbBaseObjectError):
    """Base error class for all stuff belonging to this module."""
    pass


# =============================================================================
class ScsiHost(PbBaseHandler):
    """
    Encapsulation class for SCSI hosts.
    """

    # -----------------------------------------------------------
    def __init__(
        self, host_id, wait_on_scan=DEFAULT_WAIT_ON_SCAN,
            appname=None, verbose=0, version=__version__,
            base_dir=None, use_stderr=False, simulate=False, sudo=False,
            *targs, **kwargs
            ):
        """
        Initialisation of the ScsiHost object.

        @param host_id: the numeric SCSI host Id
        @type host_id: int
        @param wait_on_scan: waiting time in seconds after scanning for a HBTL
                             for appearing the new device
        @type wait_on_scan: float
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

        self._wait_on_scan = DEFAULT_WAIT_ON_SCAN
        if wait_on_scan is not None
            self.wait_on_scan = wait_on_scan

        self.luns = []
        """
        @ivar: all found LUN devices of this SCSI host.
        @type: list of tuple, where all tuples have three integer members:
                * bus Id
                * target Id
                * LUN Id
        """

        super(ScsiHost, self).__init__(
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            initialized=False,
            simulate=simulate,
            sudo=sudo,
            *targs, **kwargs
        )

        self.init_lun_list()

        self.initialized = True

    # -----------------------------------------------------------
    @property
    def host_id(self):
        """The numeric SCSI host Id."""
        return self._host_id

    # -----------------------------------------------------------
    @property
    def hostname(self):
        """The name of the SCSI host, e.g. 'host1'."""
        return "host%d" % (self.host_id)

    # -----------------------------------------------------------
    @property
    def sysfs_dir(self):
        """
        The apropriate directory under /sys/class/scsi_host,
        e.g. '/sys/class/scsi_host/host2'
        """
        return os.path.join(BASE_SYSFS_SCSIHOST_DIR, self.hostname)

    # -----------------------------------------------------------
    @property
    def sysfs_dir_real(self):
        """The real path of the scsi_host dir in sysfs"""
        if not self.sysfs_dir:
            return None
        if not os.path.exists(self.sysfs_dir):
            return None
        return os.path.realpath(self.sysfs_dir)

    # -----------------------------------------------------------
    @property
    def exists(self):
        """Does the current scsi_host really exists?"""
        if not self.sysfs_dir:
            return False
        return os.path.exists(self.sysfs_dir)

    # -----------------------------------------------------------
    @property
    def active_mode_file(self):
        """The file containing the active mode."""
        return os.path.join(self.sysfs_dir, 'active_mode')

    # -----------------------------------------------------------
    @property
    def active_mode(self):
        """The active mode of the current SCSI host."""
        if self._active_mode is not None:
            return self._active_mode
        if not self.exists:
            return None
        self._active_mode = self.retr_active_mode()
        return self._active_mode

    # -----------------------------------------------------------
    @property
    def proc_name_file(self):
        """The file containing the name of the owning process."""
        return os.path.join(self.sysfs_dir, 'proc_name')

    # -----------------------------------------------------------
    @property
    def proc_name(self):
        """The name of the owning process of the current SCSI host."""
        if self._proc_name is not None:
            return self._proc_name
        if not self.exists:
            return None
        self._proc_name = self.retr_proc_name()
        return self._proc_name

    # -----------------------------------------------------------
    @property
    def scan_file(self):
        """The file used for scanning the SCSI host."""
        return os.path.join(self.sysfs_dir, 'scan')

    # -----------------------------------------------------------
    @property
    def state_file(self):
        """The file containing the state of the current SCSI host."""
        return os.path.join(self.sysfs_dir, 'state')

    # -----------------------------------------------------------
    @property
    def state(self):
        """The current state of the current SCSI host."""
        if self._state is not None:
            return self._state
        if not self.exists:
            return None
        self._state = self.retr_state()
        return self._state

    # -----------------------------------------------------------
    @property
    def device_dir(self):
        """The 'device directory under the main sysf dir."""
        return os.path.join(self.sysfs_dir, 'device')

    # -----------------------------------------------------------
    @property
    def device_dir_real(self):
        """The real path of the device dir in sysfs"""
        if not self.device_dir:
            return None
        if not os.path.exists(self.device_dir):
            return None
        return os.path.realpath(self.device_dir)

    # -----------------------------------------------------------
    @property
    def wait_on_scan(self):
        """
        waiting time in seconds after scanning for a HBTL
        for appearing the new device.
        """
        return self._wait_on_scan

    @wait_on_scan.setter
    def wait_on_scan(self, value):
        self._wait_on_scan = float(value)

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(ScsiHost, self).as_dict(short=short)
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
        res['wait_on_scan'] = self.wait_on_scan

        res['luns'] = []
        for hbtl in self.luns:
            res['luns'].append(str(hbtl))

        return res

    # -------------------------------------------------------------------------
    def __cmp__(self, other):
        """
        Operator overloading for the comparision function, which is implicitely
        used with the sorted function.
        """

        if not isinstance(other, ScsiHost):
            msg = _("Comparision partner %r is not a ScsiHost object.") % (other)
            raise ValueError(msg)

        return cmp(self.host_id, other.host_id)

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    def retr_active_mode(self):
        """Retrieving the current content of the active_mode_file."""

        if not self.exists:
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'active_mode', 'of': self.hostname,
                    'target': self.sysfs_dir}
            raise ScsiHostError(msg)
        if not os.path.exists(self.active_mode_file):
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'active_mode', 'of': self.hostname,
                    'target': self.active_mode_file}
            raise ScsiHostError(msg)
        if not os.access(self.active_mode_file, os.R_OK):
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r is not readable.") % {
                    'what': 'active_mode', 'of': self.hostname,
                    'target': self.active_mode_file}
            raise ScsiHostError(msg)

        return self.read_file(self.active_mode_file, quiet=True).strip()

    # -------------------------------------------------------------------------
    def retr_proc_name(self):
        """Retrieving the current content of the proc_name_file."""

        if not self.exists:
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'proc_name', 'of': self.hostname,
                    'target': self.sysfs_dir}
            raise ScsiHostError(msg)
        if not os.path.exists(self.proc_name_file):
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': 'proc_name', 'of': self.hostname,
                    'target': self.proc_name_file}
            raise ScsiHostError(msg)
        if not os.access(self.proc_name_file, os.R_OK):
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r is not readable.") % {
                    'what': 'proc_name', 'of': self.hostname,
                    'target': self.proc_name_file}
            raise ScsiHostError(msg)

        return self.read_file(self.proc_name_file, quiet=True).strip()

    # -------------------------------------------------------------------------
    def retr_state(self):
        """Retrieving the current content of the state_file."""

        if not self.exists:
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': _('state'), 'of': self.hostname,
                    'target': self.sysfs_dir}
            raise ScsiHostError(msg)
        if not os.path.exists(self.state_file):
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r doesn't exists.") % {
                    'what': _('state'), 'of': self.hostname,
                    'target': self.state_file}
            raise ScsiHostError(msg)
        if not os.access(self.state_file, os.R_OK):
            msg = _(
                "Cannot retrieve %(what)s of %(of)r, %(target)r is not readable.") % {
                    'what': _('state'), 'of': self.hostname,
                    'target': self.state_file}
            raise ScsiHostError(msg)

        return self.read_file(self.state_file, quiet=True).strip()

    # -------------------------------------------------------------------------
    def init_lun_list(self):
        """
        Initializes the list self.luns with all found luns
        of this SCSI host.
        """

        self.luns = []
        if not os.path.exists(self.device_dir):
            return

        unsorted_luns = []

        pattern = os.path.join(
            BASE_SYSFS_SCSI_DEVICES_DIR, ('%d:[0-9]*:[0-9]*:[0-9]*' % (self.host_id)))

        if self.verbose > 2:
            LOG.debug(_("Search pattern for LUNs: %r ..."), pattern)
        lun_dirs = glob.glob(pattern)

        for lun_dir in lun_dirs:

            if self.verbose > 3:
                LOG.debug(_("Checking LUN directory %r ..."), lun_dir)
            hbtl_str = os.path.basename(lun_dir)
            try:
                hbtl = HBTL.from_string(hbtl_str)
            except ValueError as e:
                if self.verbose > 2:
                    LOG.warn(
                        (_("%r is not a valid HBTL address:") % (
                            hbtl_str)) + " " + str(e))
                continue
            unsorted_luns.append(hbtl)

        self.luns = sorted(unsorted_luns)

    # -------------------------------------------------------------------------
    def target_dir(self, bus_id, target_id):
        """
        Returns the directory of the given target beyond the scsi_host
        directory in sysfs, e.g.::
            /sys/class/scsi_host/host0/device/target0:0:8
        """

        t1 = "target%d:%d:%d" % (self.host_id, bus_id, target_id)
        return os.path.join(BASE_SYSFS_SCSI_DEVICES_DIR, t1)

    # -------------------------------------------------------------------------
    def lun_dir(self, bus_id, target_id, lun_id):
        """
        Returns the directory of the given LUN beyond the scsi_host
        directory in sysfs, e.g.::
            /sys/class/scsi_host/host0/device/target0:0:8/0:0:8:0
        """

        t2 = "%d:%d:%d:%d" % (self.host_id, bus_id, target_id, lun_id)
        return os.path.join(BASE_SYSFS_SCSI_DEVICES_DIR, t2)

    # -------------------------------------------------------------------------
    def lun_block_dir(self, bus_id, target_id, lun_id):
        """
        Returns the block directory of the given LUN beyond the scsi_host
        directory in sysfs, e.g.::
            /sys/class/scsi_host/host0/device/target0:0:8/0:0:8:0/block
        """
        ldir = self.lun_dir(bus_id, target_id, lun_id)
        return os.path.join(ldir, 'block')

    # -------------------------------------------------------------------------
    def lun_blockdevicename(self, bus_id, target_id, lun_id):
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
            LOG.debug(_("Found blockdevice dirs: %s"), pp(files))
        if not files:
            return None

        bdevdir = files[0]
        bdevname = os.path.basename(bdevdir)
        if self.verbose > 3:
            msg = _(
                "Found blockdevice %(bd)r for '%(h)d:%(b)d:%(t)d:%(l)d'.") % {
                    'bd': bdevname, 'h': self.host_id,
                    'b': bus_id, 't': target_id, 'l': lun_id}
            LOG.debug(msg)

        return bdevname

    # -------------------------------------------------------------------------
    def lun_blockdevice(self, bus_id, target_id, lun_id):
        """
        Returns a ScsiDevice object of the appropriate blockdevice, if there
        is such one existing, else None is returning.
        """

        bdevname = self.lun_blockdevicename(bus_id, target_id, lun_id)
        if bdevname is None:
            return None

        dev = ScsiDevice(
            name=bdevname,
            appname=self.appname,
            verbose=self.verbose,
            base_dir=self.base_dir,
            use_stderr=self.use_stderr,
            simulate=self.simulate,
            sudo=self.sudo,
            quiet=self.quiet,
        )

        return dev

    # -------------------------------------------------------------------------
    def hbtl_blockdevice(self, hbtl):
        """
        Returns a ScsiDevice object of the appropriate blockdevice, if there
        is such one existing, else None is returning.
        """

        if hbtl.host != self.host_id:
            msg = _(
                "HBTL host Id %(hh)d does not match current host Id %(hc)d.") % {
                'hh': hbtl.host, 'hc': self.host_id}
            raise ScsiHostError(msg)

        return self.lun_blockdevice(hbtl.bus, hbtl.target, hbtl.lun)

    # -------------------------------------------------------------------------
    def scan(self, bus_id=None, target_id=None, lun_id=None):
        """
        Scans the SCSI host for a new LUN by writing 'X Y Z' into
        the scan file of the SCSI host in sysfs, where X is the given bus id,
        Y is the given target id and Z is the given LUN id.

        Failing ID's will be substituted by '-'.

        @param bus_id: the bus channel ID
        @type bus_id: int or None
        @param target_id: the target ID
        @type target_id: int or None
        @param lun_id: the new LUN Id to find
        @type lun_id: int or None

        @return: None

        """

        set_bus_id = '-'
        if bus_id is not None:
            set_bus_id = "%d" % (int(bus_id))

        set_target_id = '-'
        if target_id is not None:
            set_target_id = "%d" % (int(target_id))

        set_lun_id = '-'
        if lun_id is not None:
            set_lun_id = "%d" % (int(lun_id))

        scan_string = "%s %s %s" % (set_bus_id, set_target_id, set_lun_id)
        LOG.debug(_(
            "Scanning SCSI host %(hn)r with %(ss)r ...") % {
            'hn': self.hostname, 'ss': scan_string})

        if not os.path.exists(self.scan_file):
            msg = _(
                "Cannot scan SCSI host %(hn)r, because the file %(file)r doesn't exists.") % {
                    'hn': self.hostname, 'file': self.scan_file}
            raise ScsiHostError(msg)

        if not os.access(self.scan_file, os.W_OK):
            msg = _(
                "Cannot scan SCSI host %(hn)r, because no write access to %(file)r.") % {
                    'hn': self.hostname, 'file': self.scan_file}
            raise ScsiHostError(msg)

        self.write_file(self.scan_file, scan_string, quiet=True)

    # -------------------------------------------------------------------------
    def scan_for_hbtl(self, hbtl, quiet=False):
        """
        Scans the SCSI host for the LUN with the given HBTL info.
        It waits in some loops for the appering of the new device.

        @raise ScsiHostError: if the SCSI device does not appears
                              after some wait cycles

        @param hbtl: a HBTL object, with the information to scan for.
        @type hbtl: HBTL
        @param quiet: don't emit a warning, if the device already exists
        @type quiet: bool

        @return: an object for the new SCSI device
        @rtype: ScsiDevice

        """

        if not isinstance(hbtl, HBTL):
            msg = _("Object %r is not a HBTL object.") % (
                hbtl)
            raise ScsiHostError(msg)

        dev = self.hbtl_blockdevice(hbtl)
        if dev and dev.exists:
            msg = _("Device %(d)r for HBTL %(h)r already exists.") % {
                'd': dev.device, 'h': str(hbtl)}
            if quiet:
                LOG.debug(msg)
            else:
                LOG.warning(msg)
            return dev
        dev = None

        try_no = 0
        self.scan(hbtl.bus, hbtl.target, hbtl.lun)
        start_time = time.time()

        while not dev:
            try_no += 1
            time.sleep(0.1)
            if (try_no % 5) == 0:
                msg = _(
                    "Try number %(t)d for detecting SCSI device with HBTL %(h)r ...") % {
                    't': try_no, 'h': str(hbtl)}
            dev = self.hbtl_blockdevice(hbtl)
            if dev and dev.exists:
                msg = _(
                    "Found device %(d)s for HBTL %(h)r after %(t)d tries.") % {
                    't': try_no, 'h': str(hbtl), 'd': dev.device}
                LOG.info(msg)
                break
            dev = None
            curtime = time.time() - start_time
            if curtime >= self.wait_on_scan:
                msg = _(
                    "No device appeared for HBTL %(h)r after %(t)d tries in %(s)0.2f seconds.") % {
                    't': try_no, 'h': str(hbtl), 's': curtime}
                raise ScsiHostError(msg)

        return dev


# =============================================================================
def get_scsi_hosts(
        appname=None, verbose=0, base_dir=None, use_stderr=False,
        simulate=False, sudo=False,
        *targs, **kwargs
        ):
    """
    Returns a list of all available SCSI hosts on this machine.
    """

    pattern = os.path.join(BASE_SYSFS_SCSIHOST_DIR, 'host*')
    if verbose > 2:
        LOG.debug(_("Searching for SCSI hosts with pattern %r ..."), pattern)

    dirs = glob.glob(pattern)
    result = []

    for host_dir in dirs:
        match = RE_HOSTID.search(host_dir)
        if not match:
            LOG.warn(_("Invalid scsi_host directory %r found."), host_dir)
            continue
        host_id = int(match.group(1))
        scsi_host = ScsiHost(
            host_id,
            appname=appname,
            verbose=verbose,
            base_dir=base_dir,
            use_stderr=use_stderr,
            simulate=simulate,
            sudo=sudo,
            *targs, **kwargs
        )
        result.append(scsi_host)

    result.sort(key=lambda x: x.host_id)

    return result

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
