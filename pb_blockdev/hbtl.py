#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the HBTL object.
"""

# Standard modules
import sys
import os
import logging
import re

# Third party modules

# Own modules
from pb_base.common import pp

from pb_base.errors import PbError

from pb_blockdev.translate import translator

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.2.1'

log = logging.getLogger(__name__)

re_hbtl = re.compile(r'^(\d+):(\d+):(\d+):(\d+)$')

#==============================================================================
class HBTLError(PbError):
    """
    Base error class useable by all descendand objects.
    """
    pass

#==============================================================================
class HBTL(object):
    """
    Encapsulation class for SCSI address of the form::

        Host:Bus:Target:Lun

    """

    #--------------------------------------------------------------------------
    def __init__(self,
            host,
            bus,
            target,
            lun
            ):
        """
        Initialisation of the HBTL object.

        @raise ValueError: on invalid parameters

        @param host: host part of the HBTL address
        @type host: int
        @param bus: bus part of the HBTL address
        @type bus: int
        @param target: target part of the HBTL address
        @type target: int
        @param lun: lun part of the HBTL address
        @type lun: int

        """

        self._host = int(host)
        if self._host < 0:
            msg = _("Invalid value %(val)r for %(what)r.") % {
                    'val': host, 'what': 'host'}
            raise ValueError(msg)

        self._bus = int(bus)
        if self._bus < 0:
            msg = _("Invalid value %(val)r for %(what)r.") % {
                    'val': bus, 'what': 'bus'}
            raise ValueError(msg)

        self._target = int(target)
        if self._target < 0:
            msg = _("Invalid value %(val)r for %(what)r.") % {
                    'val': target, 'what': 'target'}
            raise ValueError(msg)

        self._lun = int(lun)
        if self._lun < 0:
            msg = _("Invalid value %(val)r for %(what)r.") % {
                    'val': lun, 'what': 'lun'}
            raise ValueError(msg)

    #------------------------------------------------------------
    @property
    def host(self):
        """The host part of the HBTL address."""
        return self._host

    #------------------------------------------------------------
    @property
    def bus(self):
        """The bus part of the HBTL address."""
        return self._bus

    #------------------------------------------------------------
    @property
    def target(self):
        """The target part of the HBTL address."""
        return self._target

    #------------------------------------------------------------
    @property
    def lun(self):
        """The lun part of the HBTL address."""
        return self._lun

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = self.__dict__
        res = {}
        for key in self.__dict__:
            if short and key.startswith('_') and not key.startswith('__'):
                continue
            val = self.__dict__[key]
            res[key] = val
        res['__class_name__'] = self.__class__.__name__
        res['__str__'] = str(self)
        res['host'] = self.host
        res['bus'] = self.bus
        res['target'] = self.target
        res['lun'] = self.lun

        return res

    #--------------------------------------------------------------------------
    @classmethod
    def from_string(cls, string):
        """
        Creating a HBTL object from the given string.

        @raise ValueError: if the given string could not evaluated.

        """

        match = re_hbtl.search(string)
        if not match:
            msg = _("Could not interprete %r as a SCSI HBTL address.") % (string)
            raise ValueError(msg)

        address = cls(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
        )

        return address

    #--------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string."""
        return "%d:%d:%d:%d" % (self.host, self.bus, self.target, self.lun)

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)
        out += "%d, " % self.host
        out += "%d, " % self.bus
        out += "%d, " % self.target
        out += "%d" % self.lun
        out +=  ")>"

        return out

    #--------------------------------------------------------------------------
    def __cmp__(self, other):
        """
        Operator overloading for the comparision function, which is implicitely
        used with the sorted function.
        """

        if not isinstance(other, HBTL):
            msg = _("Comparision partner %r is not a HBTL object.") % (other)
            raise ValueError(msg)

        res = cmp(self.host, other.host)
        if res != 0:
            return res

        res = cmp(self.bus, other.bus)
        if res != 0:
            return res

        res = cmp(self.target, other.target)
        if res != 0:
            return res

        return cmp(self.lun, other.lun)


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
