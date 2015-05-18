#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: module for base class of volume based LVM objects
"""

# Standard modules
import os
import logging

# Third party modules

# Own modules
from pb_base.common import to_bool

from pb_blockdev.lvm import GenericLvmError
from pb_blockdev.lvm import GenericLvmHandler
from pb_blockdev.lvm import DEFAULT_LVM_LOCKFILE, DEFAULT_LVM_TIMEOUT

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.2.1'

LOG = logging.getLogger(__name__)


# =============================================================================
class LvmVolumeError(GenericLvmError):
    '''
    Base error class
    '''
    pass


# =============================================================================
class LvmVolume(GenericLvmHandler):
    """
    Base class for PhysicalVolume, VolumeGroup and LogicalVolume.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, name, path, vgname, attr, uuid, used=False, discovered=None,
            lvm_command=None, lvm_lockfile=DEFAULT_LVM_LOCKFILE, lvm_timeout=DEFAULT_LVM_TIMEOUT,
            appname=None, verbose=0, version=__version__, base_dir=None,
            use_stderr=False, simulate=False, sudo=False, quiet=False, ):
        """
        Initialisation of the LVM volume object.

        @raise CommandNotFoundError: if the needed commands could not be found.
        @raise LvmVolumeError: on a uncoverable error.

        @param name: name of the LVM volume
        @type name: str
        @param path: path to the LVM volume device
        @type path: str
        @param vgname: the name of the volume group,
                       where the volume belongs to
        @type vgname: str
        @param attr: attributes of this volume
        @type attr: str
        @param uuid: the uuid of this volume
        @type uuid: uuid
        @param used: flag, showing, that this LVM volume is used
        @type used: bool
        @param discovered: is this object already discovered?
                           (True, False or None)
        @type discovered: bool or None

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
        super(LvmVolume, self).__init__(
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

        self._name = name
        """
        @ivar: the name of the LVM volume
        @type: str
        """

        self._path = path
        """
        @ivar: path to the device file (in /dev)
        @type: str
        """

        self._vgname = vgname
        """
        @ivar: the name of the volume group, where the volume belongs to
        @type: str
        """

        self.attr = attr
        """
        @ivar: attributes of this volume
        @type: str
        """

        self._uuid = uuid
        """
        @ivar: the uuid of this volume
        @type: uuid or str
        """

        self.used = used
        """
        @ivar: flag, showing, that this LVM volume is used
        @type: bool
        """

        self.properties = []
        """
        @ivar: some listed properties
        @type: list
        """

        self._extent_size = 0
        """
        @ivar: size of a single extent
        @type: int
        """

        self._total_extents = None
        """
        @ivar: total number of extents
        @type: int
        """

        self._allocated_extents = None
        """
        @ivar: number of allocated extents
        @type: int
        """

        self._free_extents = None
        """
        @ivar: number of free extents
        @type: int
        """

        self._total = None
        """
        @ivar: total volume size in Bytes
        @type: long
        """

        self._allocated = None
        """
        @ivar: allocated volume size in Bytes
        @type: long
        """

        self._free = None
        """
        @ivar: free volume size in Bytes
        @type: long
        """

        self._discovered = False
        """
        @ivar: is this object already discovered?
        @type: bool
        """
        if discovered is not None:
            self.discovered = discovered

        if self.verbose > 4:
            LOG.debug(_("Initialized."))

    # -----------------------------------------------------------
    @property
    def name(self):
        'The name of the LVM volume.'

        return self._name

    # -----------------------------------------------------------
    @property
    def path(self):
        'The device path of the LVM volume.'

        return self._path

    # -----------------------------------------------------------
    @property
    def vgname(self):
        'The name of the volume group, where the volume belongs to.'

        return self._vgname

    # -----------------------------------------------------------
    @property
    def uuid(self):
        'The UUID of this volume.'

        if not self.discovered:
            self.discover()
        return self._uuid

    # -----------------------------------------------------------
    @property
    def discovered(self):
        'Is this object already discovered?'

        return self._discovered

    @discovered.setter
    def discovered(self, value):
        self._discovered = to_bool(value)

    # -----------------------------------------------------------
    @property
    def extent_size(self):
        'The size of a single extent.'

        if not self.discovered:
            self.discover()
        return self._extent_size

    @extent_size.setter
    def extent_size(self, value):

        self._extent_size = int(value)

        if self.total_extents is not None:
            self._total = self.extent_size * self.total_extents
        else:
            self._total = None

        if self.allocated_extents is not None:
            self._allocated = self.extent_size * self.allocated_extents
        else:
            self._allocated = None

        if self.free_extents is not None:
            self._free = self.extent_size * self.free_extents
        else:
            self._free = None

    # -----------------------------------------------------------
    @property
    def extent_size_mb(self):
        """The size of a single extent in MiBytes."""
        if self.extent_size is None:
            return None
        return self.extent_size / 1024 / 1024

    # -----------------------------------------------------------
    @property
    def total_extents(self):
        'The total number of extents.'

        if not self.discovered:
            self.discover()
        return self._total_extents

    # -----------------------------------------------------------
    @property
    def allocated_extents(self):
        'The number of allocated extents.'

        if not self.discovered:
            self.discover()
        return self._allocated_extents

    # -----------------------------------------------------------
    @property
    def free_extents(self):
        'The number of free extents.'

        if not self.discovered:
            self.discover()
        return self._free_extents

    # -----------------------------------------------------------
    @property
    def total(self):
        'The total volume size in Bytes.'

        if not self.discovered:
            self.discover()
        return self._total

    # -----------------------------------------------------------
    @property
    def total_mb(self):
        """The total volume size in MiBytes."""
        if self.total is None:
            return None
        return self.total / 1024 / 1024

    # -----------------------------------------------------------
    @property
    def allocated(self):
        'The allocated volume size in Bytes.'

        if not self.discovered:
            self.discover()
        return self._allocated

    # -----------------------------------------------------------
    @property
    def allocated_mb(self):
        """The allocated volume size in MiBytes."""
        if self.allocated is None:
            return None
        return self.allocated / 1024 / 1024

    # -----------------------------------------------------------
    @property
    def free(self):
        'The free volume size in Bytes.'

        if not self.discovered:
            self.discover()
        return self._free

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(LvmVolume, self).as_dict(short=short)

        res['name'] = self.name
        res['path'] = self.path
        res['vgname'] = self.vgname
        res['discovered'] = self.discovered
        res['extent_size'] = self.extent_size
        res['extent_size_mb'] = self.extent_size_mb
        res['total_extents'] = self.total_extents
        res['allocated_extents'] = self.allocated_extents
        res['free_extents'] = self.free_extents
        res['total'] = self.total
        res['total_mb'] = self.total_mb
        res['allocated'] = self.allocated
        res['allocated_mb'] = self.allocated_mb
        res['free'] = self.free
        res['free_mb'] = self.free_mb

        return res

    # -------------------------------------------------------------------------
    def exists(self):
        """
        Checks the existence of the LVM object.

        @raise LvmVolumeError: If self.path is None (e.g. for a volume group).

        @return: exists or not
        @rtype: bool
        """

        if self.path is None:
            msg = _("No device path for %(class)s %(name)r defined.") % {
                'class': self.__class__.__name__, 'name': self.name}
            raise LvmVolumeError(msg)

        return os.path.exists(self.path)

    # -------------------------------------------------------------------------
    def discover(self):
        """
        Discovers the current LVM object by calling the appropriate LVM command
        (lvs, pvs, vgs a.s.o.)

        This method must be overwritten by inherited objects.

        @raise LvmVolumeError: on some error calling the discover command.
        @raise NotImplementedError: on calling this unoverwritten method

        """

        msg = _("Method %(method)s() of object %(class)s must be overwritten!") % {
            'method': 'discover', 'class': self.__class__.__name__}
        raise NotImplementedError(msg)

    # -------------------------------------------------------------------------
    def set_extent_count(self, total, allocated):
        """
        Sets the total, allocated and free number of extends
        of this volume.
        After then it computes the total, allocated and free space
        of this volume in Bytes.

        @param total: total number of extents
        @type total: int
        @param allocated: number of allocated extents
        @type allocated: int

        @return: None

        """

        self._total_extents = int(total)
        self._allocated_extents = int(allocated)
        self._free_extents = self._total_extents - self._allocated_extents

        self._total = self.extent_size * total
        self._allocated = self.extent_size * allocated
        self._free = self.extent_size * self.free_extents

    # -------------------------------------------------------------------------
    def get_attribute(self, position, char):
        """
        Gives back a textual description of the attribute give by the
        position in the attr string and the attr character.

        This function must be overwritten in descendant classes.

        @param position: the position in the attr string (start at 0)
        @type position: int
        @param char: the character describing the attribute
        @type char: str

        @return: attribute description
        @rtype: str

        """

        msg = _("Method %(method)s() of object %(class)s must be overwritten!") % {
            'method': 'get_attribute', 'class': self.__class__.__name__}
        raise NotImplementedError(msg)

    # -------------------------------------------------------------------------
    def attributes(self):
        """
        Gives back a list with all attributes of this volume in a
        textual format.

        @return: attributes
        @rtype: list

        """

        if self.attr is None:
            return None

        attr_str = self.attr.strip()

        i = -1
        attributes = []
        for char in attr_str:
            i += 1
            if char == '-':
                continue
            descr = self.get_attribute(i, char)
            if descr:
                attributes.append(descr)

        return attributes


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
