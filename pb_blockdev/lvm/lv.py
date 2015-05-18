#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: module for a encapsulation class of a LVM logical volume
"""

# Standard modules
import os
import logging

# Third party modules

# Own modules
from pb_base.common import to_bool

from pb_blockdev.lvm import DEFAULT_LVM_LOCKFILE, DEFAULT_LVM_TIMEOUT

from pb_blockdev.lvm.volume import LvmVolumeError
from pb_blockdev.lvm.volume import LvmVolume

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.2.0'

LOG = logging.getLogger(__name__)


# =============================================================================
class LogicalVolume(LvmVolume):
    """
    Capsulation class for LVM logical volumes.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, name, path, vgname, used=False, discovered=None, attr=None, uuid=None,
            total=None, extent_size=None, stripes=1, stripesize=0, origin=None,
            lvm_command=None, lvm_lockfile=DEFAULT_LVM_LOCKFILE, lvm_timeout=DEFAULT_LVM_TIMEOUT,
            appname=None, verbose=0, version=__version__,
            base_dir=None, use_stderr=False, simulate=False, sudo=False,
            quiet=False,
            ):
        """
        Initialisation of the LVM physical volume object.

        @raise CommandNotFoundError: if the needed commands could not be found.
        @raise LvmVolumeError: on a uncoverable error.

        @param name: name of the LVM physical volume
        @type name: str
        @param path: path to the device file (under /dev)
        @type path: str
        @param vgname: name of the volume group, where this PV belongs to,
                       maybe None
        @type vgname: str
        @param used: is this PV initialized
        @type used: bool
        @param discovered: is this object already discovered?
                           (True, False or None)
        @type discovered: bool or None
        @param attr: attributes of this logical volume
        @type attr: str
        @param uuid: the UUID of this logical volume
        @type uuid: uuid
        @param total: total size of this PV in Bytes
        @type total: int
        @param extent_size: size of one extent in Bytes
        @type extent_size: int
        @param stripes: number of stripes of this LV
        @type stripes: int
        @param stripesize: size of a stripe in Bytes
        @type stripesize: int
        @param origin: the origin device of a snapshot volume (LV name)
        @type origin: str

        @param lvm_command: path to executable 'lvm' command
        @type lvm_command: str
        @param lvm_lockfile: the global lockfile used for lvm execution
        @type lvm_lockfile: str
        @param lvm_timeout: timeout for execution the lvm command
        @type lvm_timeout: int or None

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
        @param quiet: don't display ouput of action after calling
        @type quiet: bool

        @return: None
        """

        # Initialisation of the parent object
        super(LogicalVolume, self).__init__(
            name=name,
            path=path,
            vgname=vgname,
            attr=attr,
            uuid=uuid,
            used=used,
            discovered=discovered,
            lvm_command=lvm_command,
            lvm_lockfile=lvm_lockfile,
            lvm_timeout=lvm_timeout,
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )

        if self.discovered:
            self.extent_size = int(extent_size)
            extents_total = int(total / self.extent_size)
            self.set_extent_count(extents_total, extents_total)

        self._stripes = int(stripes)
        """
        @ivar: number of stripes of this LV
        @type: int
        """

        self._stripesize = long(stripesize)
        """
        @ivar: size of a stripe in Bytes
        @type: long
        """

        self._origin = origin
        """
        @ivar: the origin device of a snapshot volume (LV name)
        @type: str
        """

        self.devices = []
        """
        @ivar: list of all PVs, where this LV lies as tuples
               with the PV device name and the number of the start extent
        @type: list of tuples
        """

        self.initialized = True

    # -----------------------------------------------------------
    @property
    def stripes(self):
        'The number of stripes of this LV.'

        if not self.discovered:
            self.discover()
        return self._stripes

    # -----------------------------------------------------------
    @property
    def stripesize(self):
        'The size of a stripe in Bytes.'

        if not self.discovered:
            self.discover()
        return self._stripesize

    # -----------------------------------------------------------
    @property
    def origin(self):
        'The origin device of a snapshot volume (LV name).'

        if not self.discovered:
            self.discover()
        return self._origin

    # -----------------------------------------------------------
    @property
    def dm_path(self):
        "The absolute path to the appropriate DM device."

        if not self.path:
            return None
        if not os.path.exists(self.path):
            return None
        return os.path.realpath(self.path)

    # -----------------------------------------------------------
    @property
    def is_snapshot(self):
        """Returns, whether the current LV is a snapshot volume."""

        if not self.discovered:
            self.discover()

        if self.origin:
            return True
        return False

    # -----------------------------------------------------------
    @property
    def is_origin(self):
        """Returns, whether the current LV is the origin of a snapshot."""

        if not self.discovered:
            self.discover()

        if not self.attr:
            return None

        attr_str = self.attr.strip()
        if attr_str[0] == 'o' or attr_str[0] == 'O':
            return True
        return False

    # -----------------------------------------------------------
    @property
    def is_opened(self):
        """The current device is currently opened by another process."""

        if not self.discovered:
            self.discover()

        if not self.attr:
            return None

        attr_str = self.attr.strip()
        if attr_str[5] == 'o':
            return True
        return False

    # -----------------------------------------------------------
    @property
    def opened(self):
        """The current device is currently opened by another process."""
        return self.is_opened

    # -----------------------------------------------------------
    @property
    def dm_name(self):
        """The name of the appropriate device mapper device."""
        if not self.vgname:
            return None
        if not self.name:
            return None

        vname = self.vgname.replace('-', '--')
        lname = self.name.replace('-', '--')
        return vname + '-' + lname

    # -----------------------------------------------------------
    @property
    def origin_dm_name(self):
        """
        The name of the device mapper device of the origin, if
        the current device is a snapshot.
        """

        if not self.vgname:
            return None
        if not self.origin:
            return None

        vname = self.vgname.replace('-', '--')
        oname = self.origin.replace('-', '--')
        return vname + '-' + oname

    # -----------------------------------------------------------
    @property
    def snap_real_name(self):
        """
        The name of the device mapper device of the real origin,
        if the current device is a snapshot.
        """

        if not self.origin_dm_name:
            return None

        return self.origin_dm_name + '-real'

    # -----------------------------------------------------------
    @property
    def snap_cow_name(self):
        """
        The name of the device mapper device of the COW device,
        if the current device is a snapshot.
        """

        if not self.dm_name:
            return None
        if not self.origin:
            return None

        return self.dm_name + '-cow'

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(LogicalVolume, self).as_dict(short=short)

        res['stripes'] = self.stripes
        res['stripesize'] = self.stripesize
        res['origin'] = self.origin
        res['dm_path'] = self.dm_path
        res['is_snapshot'] = self.is_snapshot
        res['is_origin'] = self.is_origin
        res['is_opened'] = self.is_opened
        res['dm_name'] = self.dm_name
        res['origin_dm_name'] = self.origin_dm_name
        res['snap_real_name'] = self.snap_real_name
        res['snap_cow_name'] = self.snap_cow_name

        return res

    # -------------------------------------------------------------------------
    def add_device(self, device, start_extent=0):
        """
        Adds the given device to the list of devices self.devices.

        @param device: the device name
        @type device: str
        @param start_extent: the number of the start extent on this PV
        @type start_extent: int

        @return: None

        """

        self.devices.append((device, start_extent))

    # -------------------------------------------------------------------------
    def get_attribute(self, position, char):
        """
        Gives back a textual description of the attribute give by the
        position in the attr string and the attr character.

        @param position: the position in the attr string (start at 0)
        @type position: int
        @param char: the character describing the attribute
        @type char: str

        @return: attribute description
        @rtype: str

        """

        descr = "unknown_%s" % (char)
        if position == 0:
            if char == 'm':
                descr = 'mirrored'
            elif char == 'M':
                descr = 'mirrored_wo_init_sync'
            elif char == 'o':
                descr = 'origin'
            elif char == 'O':
                descr = 'origin_w_merging_snapshot'
            elif char == 'r':
                descr = 'raid'
            elif char == 'R':
                descr = 'raid_wo_init_sync'
            elif char == 's':
                descr = 'snapshot'
            elif char == 'S':
                descr = 'merging_snapshot'
            elif char == 'p':
                descr = 'pvmove'
            elif char == 'v':
                descr = 'virtual'
            elif char == 'i':
                descr = 'raid_image'
            elif char == 'I':
                descr = 'raid_image_oo_sync'
            elif char == 'l':
                descr = 'log_device'
            elif char == 'c':
                descr = 'under_conversion'
            elif char == 'V':
                descr = 'thin_volume'
            elif char == 't':
                descr = 'thin_pool'
            elif char == 'T':
                descr = 'thin_pool_data'
            elif char == 'm':
                descr = 'metadata'
        elif position == 1:
            if char == 'w':
                descr = 'writeable'
            elif char == 'r':
                descr = 'read_only'
            elif char == 'R':
                descr = 'read_only_activation'
        elif position == 2:
            if char == 'c':
                descr = 'alloc_contiguous',
            elif char == 'l':
                descr = 'alloc_cling'
            elif char == 'n':
                descr = 'alloc_normal'
            elif char == 'a':
                descr = 'alloc_anywhere'
            elif char == 'i':
                descr = 'alloc_inherited'
        elif position == 3:
            if char == 'm':
                descr = 'fixed_minor'
        elif position == 4:
            if char == 'a':
                descr = 'activated'
            elif char == 's':
                descr = 'suspended'
            elif char == 'I':
                descr = 'invalid_snapshot'
            elif char == 'S':
                descr = 'invalid_suspendes_snapshot'
            elif char == 'm':
                descr = 'merge_failed'
            elif char == 'M':
                descr = 'suspended_snap_merge_failed'
            elif char == 'd':
                descr = 'mapped_dev_wo_table'
            elif char == 'i':
                descr = 'mapped_dev_w_inactive_table'
        elif position == 5:
            if char == 'o':
                descr = 'device_open'
        elif position == 6:
            if char == 'm':
                descr = 'target_mirror'
            elif char == 'r':
                descr = 'target_raid'
            elif char == 's':
                descr = 'target_snapshot'
            elif char == 't':
                descr = 'target_thin'
            elif char == 'u':
                descr = 'target_unknown'
            elif char == 'v':
                descr = 'target_virtual'
        elif position == 7:
            if char == 'z':
                descr = 'zeroed'

        return descr

    # -------------------------------------------------------------------------
    def discover(self):
        """
        Discovers the current LV object by calling 'lvs'

        @raise LvmVolumeError: on some error calling the discover command.

        @return: success of discovering

        """

        cname = self.vgname + '/' + self.name

        if not self.exists():
            if self.verbose > 2:
                LOG.debug(
                    _("LV %r doesn't exists, discovery not possible."), cname)
            return False

        if self.verbose > 2:
            LOG.debug(_("Discovering logical volume %r ..."), cname)

        self.discovered = False
        self.devices = []

        attr_params = "lv_name,vg_name,stripes,stripesize,lv_attr,lv_uuid,"
        attr_params += "devices,lv_path,vg_extent_size,lv_size,origin"

        cmd_params = [
            "lvs",
            "--nosuffix",
            "--noheadings",
            "--units",
            "b",
            "--separator",
            ";",
            "-o",
            attr_params,
            cname
        ]

        (ret_code, std_out, std_err) = self.exec_lvm(
            cmd_params, quiet=True, simulate=False, force=True)
        if ret_code:
            if ret_code == 5:
                LOG.debug(_("Logical volume %r not found."), cname)
                return False
            msg = _("Error %(rc)d getting LVM logical volume %(name)s: %(msg)s") % {
                'rc': ret_code, 'name': cname, 'msg': std_err}
            raise LvmVolumeError(msg)

        lines = std_out.split('\n')

        devices = ''

        for line in lines:

            line = line.strip()
            if line == '':
                continue

            words = line.split(";")

            # lvname = words[0].strip()
            # vgname = words[1].strip()
            stripes = int(words[2])
            stripesize = int(words[3])
            attr = words[4].strip()
            uuid = words[5].strip()
            devices = words[6].strip()
            path = words[7].strip()
            extent_size = int(words[8])
            total = int(words[9])
            origin = words[10].strip()
            if origin == '':
                origin = None

            self._stripes = stripes
            self._stripesize = stripesize
            self._path = path
            self.attr = attr
            self._uuid = uuid
            self._origin = origin

            self.used = True

            self.discovered = True

            self.extent_size = extent_size
            extents_total = total / extent_size
            self.set_extent_count(extents_total, extents_total)

            break

        if self.discovered:
            match = re.search(r'(.*)\((\d+)\)', devices)
            if match:
                self.add_device(match.group(1), int(match.group(2)))

        return self.discovered

    # -------------------------------------------------------------------------
    def rename(self, new_name):
        """
        Renames the current logical volume inside the volume group
        to the new name.

        @param new_name: the new name to set
        @type new_name: str

        """

        if not new_name:
            raise LvmVolumeError(_("No new name for logical volume given."))

        new_name = str(new_name).strip()
        if new_name == '':
            raise LvmVolumeError(_("Empty name for logical volume given."))

        if new_name == self.name:
            LOG.debug(_("New logical volume name is equal the current name %r."),
                new_name)
            return

        cur_cname = self.vgname + '/' + self.name
        new_cname = self.vgname + '/' + new_name

        cmd_params = [
            'lvrename',
            self.vgname,
            self.name,
            new_name
        ]

        LOG.info(_("Renaming logical volume %(old)r to %(new)r.") % {
            'old': cur_cname, 'new': new_cname})

        (ret_code, std_out, std_err) = self.exec_lvm(
            cmd_params, quiet=True, force=False)

        self._name = new_name

        return

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
