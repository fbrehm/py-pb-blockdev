#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: Module for a base blockdevice class
"""

# Standard modules
import sys
import os
import logging
import re

from gettext import gettext as _

# Third party modules

# Own modules
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.object import PbBaseObjectError

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

__version__ = '0.2.0'

log = logging.getLogger(__name__)

#---------------------------------------------
# Some module variables

base_sysfs_blockdev_dir = os.sep + os.path.join('sys', 'block')
re_major_minor = re.compile('^\s*(\d+):(\d+)')

#==============================================================================
class BlockDeviceError(PbBaseHandlerError):
    """
    Base error class for all exceptions belonging to base block device
    """

    pass

#==============================================================================
class BlockDevice(PbBaseHandler):
    """
    Base block device object.
    """

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
        Initialisation of the base blockdevice object.

        @raise CommandNotFoundError: if some needed commands could not be found.
        @raise BlockDeviceError: on a uncoverable error.

        @param name: name of the blockdevice, like used under /sys/block.
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

        super(BlockDevice, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
                simulate = simulate,
                sudo = False,
                quiet = False,
        )

        self._name = name
        """
        @ivar: name of the blockdevice, like used under /sys/block
        @type: None (if not even discoverd) or str
        """

        self._major_number = None
        """
        @ivar: the major device number
        @type: int
        """

        self._minor_number = None
        """
        @ivar: the minor device number
        @type: int
        """

        self._removable = None
        """
        @ivar: flag, whether the device is removeable, e.g. CD-ROM
        @type: bool
        """

        self._readonly = None
        """
        @ivar: flage, whether the device is radonly, e.g. CD-ROM
        @type: bool
        """

    #------------------------------------------------------------
    @property
    def name(self):
        """The name of the blockdevice, like used under /sys/block"""
        return getattr(self, '_name', None)

    @name.setter
    def name(self, value):
        if not value:
            msg = _("No new name given.")
            raise BlockDeviceError(msg)
        new_name = str(value).strip()
        if not new_name:
            msg = _("Empty name %r given as name of the blockdevice.") % (
                    value)
            raise BlockDeviceError(msg)
        self._name = new_name

    #------------------------------------------------------------
    @property
    def device(self):
        """The file name of the approriate device file under /dev."""
        if not self.name:
            return None
        return os.sep + os.path.join('dev', self.name)

    #------------------------------------------------------------
    @property
    def sysfs_bd_dir(self):
        """The apropriate directory under /sys/block, e.g. /sys/block/sda"""
        if not self.name:
            return None
        return os.path.join(base_sysfs_blockdev_dir, self.name)

    #------------------------------------------------------------
    @property
    def sysfs_dev_file(self):
        """The file in sysfs containing the major:minor number of the device."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'dev')

    #------------------------------------------------------------
    @property
    def sysfs_removable_file(self):
        """The file in sysfs containing whether the device is removable."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'removable')

    #------------------------------------------------------------
    @property
    def sysfs_ro_file(self):
        """The file in sysfs containing whether the device is readonly."""
        if not self.sysfs_bd_dir:
            return None
        return os.path.join(self.sysfs_bd_dir, 'ro')

    #------------------------------------------------------------
    @property
    def exists(self):
        """Does the blockdevice of the current object exists?"""
        sfs_dir = self.sysfs_bd_dir
        if not sfs_dir:
            return False
        if os.path.exists(sfs_dir):
            return True
        return False

    #------------------------------------------------------------
    @property
    def major_number(self):
        """The major device number."""
        if self._major_number is not None:
            return self._major_number
        if not self.exists:
            return None
        self.retr_major_minor()
        return self._major_number

    #------------------------------------------------------------
    @property
    def minor_number(self):
        """The minor device number."""
        if self._minor_number is not None:
            return self._minor_number
        if not self.exists:
            return None
        self.retr_major_minor()
        return self._minor_number

    #------------------------------------------------------------
    @property
    def major_minor_number(self):
        """The major and the minor number together."""
        if self.major_number is None or self.minor_number is None:
            return None
        return "%d:%d" % (self.major_number, self.minor_number)

    #------------------------------------------------------------
    @property
    def removable(self):
        """A flag, whether the device is removeable, e.g. CD-ROM."""
        if self._removable is not None:
            return self._removable
        if not self.exists:
            return None
        self.retr_removable()
        return self._removable

    #------------------------------------------------------------
    @property
    def readonly(self):
        """A flag, whether the device is readonly, e.g. CD-ROM."""
        if self._readonly is not None:
            return self._readonly
        if not self.exists:
            return None
        self.retr_readonly()
        return self._readonly

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(BlockDevice, self).as_dict()
        res['device'] = self.device
        res['sysfs_bd_dir'] = self.sysfs_bd_dir
        res['sysfs_dev_file'] = self.sysfs_dev_file
        res['sysfs_removable_file'] = self.sysfs_removable_file
        res['sysfs_ro_file'] = self.sysfs_ro_file
        res['exists'] = self.exists
        res['removable'] = self.removable
        res['readonly'] = self.readonly
        res['major_number'] = self.major_number
        res['minor_number'] = self.minor_number
        res['major_minor_number'] = self.major_minor_number

        return res

    #--------------------------------------------------------------------------
    def retr_removable(self):
        """
        A method to retrieve whether the device is a removable device.

        @raise BlockDeviceError: if the removable file in sysfs doesn't exits
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve removable state, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve removable state of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_removable_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve removable state of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve removable state of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve removable state of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if f_content == '1':
            self._removable = True
        else:
            self._removable = False

    #--------------------------------------------------------------------------
    def retr_readonly(self):
        """
        A method to retrieve whether the device is a readonly device.

        @raise BlockDeviceError: if the readonly file in sysfs doesn't exits
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve readonly state, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve readonly state of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        r_file = self.sysfs_ro_file
        if not os.path.exists(r_file):
            msg = _("Cannot retrieve readonly state of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if not os.access(r_file, os.R_OK):
            msg = _("Cannot retrieve readonly state of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(r_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve readonly state of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': r_file}
            raise BlockDeviceError(msg)

        if f_content == '1':
            self._readonly = True
        else:
            self._readonly = False

    #--------------------------------------------------------------------------
    def retr_major_minor(self):
        """
        A method to retrieve the major/minor number of the device form the
        appropriate dev file in sysfs. These numbers are saved in
        self._major_number and self._minor_number.

        @raise BlockDeviceError: if the dev file in sysfs doesn't exits
                                 or could not read

        """

        if not self.name:
            msg = _("Cannot retrieve major/minor number, because it's an " +
                    "unnamed block device object.")
            raise BlockDeviceError(msg)

        if not self.exists:
            msg = _("Cannot retrieve major/minor number of %r, because the " +
                    "block device doesn't exists.") % (self.name)
            raise BlockDeviceError(msg)

        dev_file = self.sysfs_dev_file
        if not os.path.exists(dev_file):
            msg = _("Cannot retrieve major/minor number of %(bd)r, because the " +
                    "file %(file)r doesn't exists.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        if not os.access(dev_file, os.R_OK):
            msg = _("Cannot retrieve major/minor number of %(bd)r, because no " +
                    "read access to %(file)r.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        f_content = self.read_file(dev_file, quiet = True).strip()
        if not f_content:
            msg = _("Cannot retrieve major/minor number of %(bd)r, because " +
                    "file %(file)r has no content.") % {
                    'bd': self.name, 'file': dev_file}
            raise BlockDeviceError(msg)

        match = re_major_minor.search(f_content)
        if not match:
            msg = _("Cannot retrieve major/minor number of %(bd)r, bacause " +
                    "cannot evaluate content of %(file)r: %(cont)r") % {
                    'bd': self.name, 'file': dev_file, 'cont': f_content}
            raise BlockDeviceError(msg)

        self._major_number = int(match.group(1))
        self._minor_number = int(match.group(2))

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
