#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the MegaraidLogicalDrive class
"""

# Standard modules
import sys
import os
import logging
import re

# Third party modules

# Own modules
import pb_base
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust
from pb_base.common import caller_search_path

from pb_base.errors import PbError

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

from pb_blockdev.megaraid import MegaraidError
from pb_blockdev.megaraid import MegaraidLdError

from pb_blockdev.megaraid.pd import MegaraidPd

__version__ = '0.3.3'

log = logging.getLogger(__name__)

# RAID Level          : Primary-1, Secondary-0, RAID Level Qualifier-0
raid_level_pattern = r'^RAID\s+Level\s*:\s*'
raid_level_pattern += r'Primary-(\d+)'
raid_level_pattern += r',\s*Secondary-(\d+)'
raid_level_pattern += r'(?:,\s*RAID\s+Level\s+Qualifier-(\d+))?'
re_raid_level = re.compile(raid_level_pattern, re.IGNORECASE)
del raid_level_pattern

# Virtual Drive Type    : CacheCade
re_drive_type = re.compile(r'^Virtual\s+Drive\s+Type\s*:\s*(\S.*)',
        re.IGNORECASE)
re_cachecade = re.compile(r'^\s*CacheCade\s*$', re.IGNORECASE)

# Name                :
re_name = re.compile(r'^Name\s*:\s*(\S.*)', re.IGNORECASE)

# Size                : 2.728 TB
re_size = re.compile(r'^Size\s*:\s*(\S.*)', re.IGNORECASE)

# State               : Optimal
re_state = re.compile(r'^State\s*:\s*(\S.*)', re.IGNORECASE)

# PD: 0 Information
re_start_pd = re.compile(r'^PD\s*:\s*(\d+)\s*Information\s*$', re.IGNORECASE)

# Enclosure Device ID: 9
re_pd_enc = re.compile(r'^Enclosure\s+Device\s+ID\s*:\s*(\d+)\s*$',
        re.IGNORECASE)

# Slot Number: 0
re_pd_slot = re.compile(r'^Slot\s+Number\s*:\s*(\d+)\s*$', re.IGNORECASE)

# Is VD Cached: No
re_cached = re.compile(r'^Is\s+VD\s+Cached\s*:\s*(\S.*)', re.IGNORECASE)

re_yes = re.compile(r'^\s*y(?:es)?\s*$', re.IGNORECASE)

# Cache Cade Type : Read Only
# Cache Cade Type : Read and Write
re_cache_rw = re.compile(r'^Cache\s+Cade\s+Type\s*:\s*(\S.*)', re.IGNORECASE)
re_rw = re.compile(r'^\s*Read\s+and\s+Write\s*$', re.IGNORECASE)

#==============================================================================
class MegaraidLogicalDrive(PbBaseObject):
    """
    Encapsulation class for a Megaraid Logical Drive (LD)
    """

    #------------------------------------------------------------
    def __init__(self,
            adapter,
            number,
            target_id = None,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            ):
        """
        Initialisation of the megaraid Logical Drive object.

        @param adapter: the Id of the Megaraid controller
        @type adapter: int
        @param number: the number of the Logical Drive on the Megaraid controller
        @type number: int
        @param id: the SCSI target Id of the Logical Drive
        @type id: int
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

        @return: None

        """

        self._adapter = int(adapter)
        self._number = int(number)
        self._target_id = None
        if target_id is not None:
            self._target_id = int(target_id)

        super(MegaraidLogicalDrive, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
        )

        self._name = None
        self._raid_level_primary = None
        self._raid_level_secondary = None
        self._raid_level_qualifier = None
        self._size = None
        self._state = None
        self._drive_type = None

        self._cached = False
        self._cache_rw = None

        self.pds = []
        """
        @ivar: list of all physical drives belonging to this LD
        @type: list of MegaraidPd
        """

        self.initialized = True

    #------------------------------------------------------------
    @property
    def adapter(self):
        """The Id of the Megaraid controller."""
        return self._adapter

    #------------------------------------------------------------
    @property
    def number(self):
        """The number of the Logical Drive on the Megaraid controller."""
        return self._number

    #------------------------------------------------------------
    @property
    def target_id(self):
        """The SCSI target Id of the Logical Drive."""
        return self._target_id

    @target_id.setter
    def target_id(self, value):
        tid = int(value)
        if tid < 0:
            raise ValueError("The SCSI target Id must be a positive integer value.")
        self._target_id = tid

    #------------------------------------------------------------
    @property
    def drive_type(self):
        """The drive type of the LD."""
        return self._drive_type

    #------------------------------------------------------------
    @property
    def is_cachecade_drive(self):
        """Flag, whether the current LD is a CacheCade drive or not."""
        if self.drive_type is None:
            return False
        if re_cachecade.search(self.drive_type):
            return True
        return False

    #------------------------------------------------------------
    @property
    def name(self):
        """The name of the Logical Drive."""
        return self._name

    #------------------------------------------------------------
    @property
    def raid_level_primary(self):
        """The primary RAID level."""
        return self._raid_level_primary

    #------------------------------------------------------------
    @property
    def raid_level_secondary(self):
        """The secondary RAID level."""
        return self._raid_level_secondary

    #------------------------------------------------------------
    @property
    def raid_level_qualifier(self):
        """The RAID level Qualifier."""
        return self._raid_level_qualifier

    #------------------------------------------------------------
    @property
    def raid_level(self):
        """The textual representation of the RAID level."""

        if (self.raid_level_primary is None or
                self.raid_level_secondary is None):
            return None

        if self.raid_level_primary == 0:
            if self.raid_level_secondary == 0:
                return "RAID-0"

        if self.raid_level_primary == 1:
            if self.raid_level_secondary == 0:
                return "RAID-1"
            if self.raid_level_secondary == 3:
                return "RAID-10"

        if self.raid_level_primary == 5:
            if self.raid_level_secondary == 0 and self.raid_level_qualifier == 3:
                return "RAID-5"
            if self.raid_level_secondary == 3 and self.raid_level_qualifier == 3:
                return "RAID-50"

        if self.raid_level_primary == 6:
            if self.raid_level_secondary == 0 and self.raid_level_qualifier == 3:
                return "RAID-6"
            if self.raid_level_secondary == 3 and self.raid_level_qualifier == 3:
                return "RAID-60"

        return "RAID-%d:%d:%d(?)" % (self.raid_level_primary,
                self.raid_level_secondary, self.raid_level_qualifier)

    #------------------------------------------------------------
    @property
    def size(self):
        """Textual description of the size."""
        return self._size

    #------------------------------------------------------------
    @property
    def state(self):
        """Textual description of the drive state."""
        return self._state

    #------------------------------------------------------------
    @property
    def cached(self):
        """Is this LD cached by CacheCade?"""
        return self._cached

    #------------------------------------------------------------
    @property
    def cache_rw(self):
        """Is this a read/write cache by CacheCade?"""
        return self._cache_rw

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MegaraidLogicalDrive, self).as_dict(short = short)
        res['adapter'] = self.adapter
        res['number'] = self.number
        res['target_id'] = self.target_id
        res['name'] = self.name
        res['drive_type'] = self.drive_type
        res['is_cachecade_drive'] = self.is_cachecade_drive
        res['state'] = self.state
        res['size'] = self.size
        res['raid_level'] = self.raid_level
        res['raid_level_primary'] = self.raid_level_primary
        res['raid_level_secondary'] = self.raid_level_secondary
        res['raid_level_qualifier'] = self.raid_level_qualifier
        res['cached'] = self.cached
        res['cache_rw'] = self.cache_rw

        res['pds'] = []
        for pd in self.pds:
            res['pds'].append(pd.as_dict(short = short))

        return res

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("adapter=%r" % (self.adapter))
        fields.append("number=%r" % (self.number))
        if self.target_id is not None:
            fields.append("target_id=%r" % (self.target_id))
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("version=%r" % (self.version))
        fields.append("base_dir=%r" % (self.base_dir))
        fields.append("use_stderr=%r" % (self.use_stderr))
        fields.append("initialized=%r" % (self.initialized))

        out += ", ".join(fields) + ")>"
        return out

    #--------------------------------------------------------------------------
    def __cmp__(self, other):
        """
        Operator overloading for the comparision function, which is implicitely
        used with the sorted function.
        """

        if not isinstance(other, MegaraidLogicalDrive):
            msg = "Comparision partner %r is not a MegaraidLogicalDrive object." % (other)
            raise ValueError(msg)

        res = cmp(self.adapter, other.adapter)
        if res != 0:
            return res

        return cmp(self.number, other.number)

    #--------------------------------------------------------------------------
    def init_from_lines(self, lines, no_override = False):
        """
        Init of all properties from output lines from 'MegaCLI -LdPdInfo' or
        'MegaCLI -LdInfo'.

        @param lines: the output lines from MegaCLI to inspect
        @type lines: str or list of str
        @param no_override: don't reset all properties before inspecting
        @type no_override: bool

        """

#       The Output looks like:
#
#       Name                :
#       RAID Level          : Primary-1, Secondary-0, RAID Level Qualifier-0
#       Size                : 55.375 GB
#       Sector Size         : 512
#       Is VD emulated      : No
#       Mirror Data         : 55.375 GB
#       State               : Optimal
#       Strip Size          : 256 KB
#       Number Of Drives    : 2
#       Span Depth          : 1
#       Default Cache Policy: WriteBack, ReadAdaptive, Direct, No Write Cache if Bad BBU
#       Current Cache Policy: WriteBack, ReadAdaptive, Direct, No Write Cache if Bad BBU
#       Default Access Policy: Read/Write
#       Current Access Policy: Read/Write
#       Disk Cache Policy   : Enabled
#       Encryption Type     : None
#       PI type: No PI
#
#       Is VD Cached: No
#       Number of Spans: 1
#       Span: 0 - Number of PDs: 2
#
#       PD: 0 Information
#       Enclosure Device ID: 9
#       Slot Number: 0
#       Drive's position: DiskGroup: 0, Span: 0, Arm: 0
#       Enclosure position: 1
#       Device Id: 32
#       WWN: 50015178f36b244d
#       Sequence Number: 2
#       Media Error Count: 0
#       Other Error Count: 0
#       Predictive Failure Count: 0
#       Last Predictive Failure Event Seq Number: 0
#       PD Type: SATA
#
#       Raw Size: 55.899 GB [0x6fccf30 Sectors]
#       Non Coerced Size: 55.399 GB [0x6eccf30 Sectors]
#       Coerced Size: 55.375 GB [0x6ec0000 Sectors]
#       Sector Size:  512
#       Logical Sector Size:  512
#       Physical Sector Size:  512
#       Firmware state: Online, Spun Up
#       Commissioned Spare : No
#       Emergency Spare : No
#       Device Firmware Level: 400i
#       Shield Counter: 0
#       Successful diagnostics completion on :  N/A
#       SAS Address(0): 0x500304800058338c
#       Connected Port Number: 0(path0)
#       Inquiry Data: CVCV3053035K060AGN  INTEL SSDSC2CW060A3                     400i
#       FDE Capable: Not Capable
#       FDE Enable: Disable
#       Secured: Unsecured
#       Locked: Unlocked
#       Needs EKM Attention: No
#       Foreign State: None
#       Device Speed: 6.0Gb/s
#       Link Speed: 6.0Gb/s
#       Media Type: Solid State Device
#       Drive:  Not Certified
#       Drive Temperature : N/A
#       PI Eligibility:  No
#       Drive is formatted for PI information:  No
#       PI: No PI
#       Port-0 :
#       Port status: Active
#       Port's Linkspeed: 6.0Gb/s
#       Drive has flagged a S.M.A.R.T alert : No
#
#
#
#
#       PD: 1 Information
#       Enclosure Device ID: 9
#       Slot Number: 1
#       Drive's position: DiskGroup: 0, Span: 0, Arm: 1
#       Enclosure position: 1
#       Device Id: 33
#       WWN: 50015178f36b1102
#       Sequence Number: 2
#       Media Error Count: 0
#       Other Error Count: 0
#       Predictive Failure Count: 0
#       Last Predictive Failure Event Seq Number: 0
#       PD Type: SATA
#
#       Raw Size: 55.899 GB [0x6fccf30 Sectors]
#       Non Coerced Size: 55.399 GB [0x6eccf30 Sectors]
#       Coerced Size: 55.375 GB [0x6ec0000 Sectors]
#       Sector Size:  512
#       Logical Sector Size:  512
#       Physical Sector Size:  512
#       Firmware state: Online, Spun Up
#       Commissioned Spare : No
#       Emergency Spare : No
#       Device Firmware Level: 400i
#       Shield Counter: 0
#       Successful diagnostics completion on :  N/A
#       SAS Address(0): 0x500304800058338d
#       Connected Port Number: 0(path0)
#       Inquiry Data: CVCV30530085060AGN  INTEL SSDSC2CW060A3                     400i
#       FDE Capable: Not Capable
#       FDE Enable: Disable
#       Secured: Unsecured
#       Locked: Unlocked
#       Needs EKM Attention: No
#       Foreign State: None
#       Device Speed: 6.0Gb/s
#       Link Speed: 6.0Gb/s
#       Media Type: Solid State Device
#       Drive:  Not Certified
#       Drive Temperature : N/A
#       PI Eligibility:  No
#       Drive is formatted for PI information:  No
#       PI: No PI
#       Port-0 :
#       Port status: Active
#       Port's Linkspeed: 6.0Gb/s
#       Drive has flagged a S.M.A.R.T alert : No
#
#
#
#

        self.initialized = False

        if self.verbose > 3:
            log.debug("Analyzing lines:\n%s", pp(lines))

        if not no_override:
            self._name = None
            self._raid_level_primary = None
            self._raid_level_secondary = None
            self._raid_level_qualifier = None
            self._size = None
            self._state = None
            self._cached = False
            self._cache_rw = None

        pd_lines = []

        pd_nr = None
        pd_enc = None
        pd_slot = None
        pd = None

        for line in lines:

            # Checking for the Drive type
            match = re_drive_type.search(line)
            if match:
                self._drive_type = match.group(1)
                continue

            # Checking for RAID level
            match = re_raid_level.search(line)
            if match:
                self._raid_level_primary = int(match.group(1))
                self._raid_level_secondary = int(match.group(2))
                if match.group(3) is not None:
                    self._raid_level_qualifier = int(match.group(3))
                if self.verbose > 2:
                    log.debug("RAID level of LD No %d: %s.",
                            self.number, self.raid_level)
                continue

            # Checking for the name of the LD
            match = re_name.search(line)
            if match:
                self._name = match.group(1)
                if self.verbose > 2:
                    log.debug("Got %r as name of LD %d.", self.name, self.number)
                continue

            # Checking for the text size
            match = re_size.search(line)
            if match:
                self._size = match.group(1)
                if self.verbose > 2:
                    log.debug("Got %r as size of LD %d.", self.size, self.number)
                continue

            # Checking for the state
            match = re_state.search(line)
            if match:
                self._state = match.group(1)
                if self.verbose > 3:
                    log.debug("Got %r as state of LD %d.", self.state, self.number)
                continue

            # Check for cache state
            match = re_cached.search(line)
            if match:
                cached = match.group(1)
                if re_yes.search(cached):
                    self._cached = True
                else:
                    self._cached = False
                continue

            # Check, whether the cache is r/w
            match = re_cache_rw.search(line)
            if match:
                ctype = match.group(1)
                if re_rw.search(ctype):
                    self._cache_rw = True
                else:
                    self._cache_rw = False

            # Check for start of a ne PD definition
            match = re_start_pd.search(line)
            if match:
                pd_nr = int(match.group(1))
                if pd_lines and pd_enc is not None and pd_slot is not None:
                    if pd:
                        self.pds.append(pd)
                    if self.verbose > 2:
                        log.debug("Init of PD [%d:%d] of LD %d.",
                                pd_enc, pd_slot, self.number)
                    pd = MegaraidPd(
                            adapter = self.adapter,
                            enclosure = pd_enc,
                            slot = pd_slot,
                            appname = self.appname,
                            verbose  = self.verbose,
                            base_dir = self.base_dir,
                            use_stderr = self.use_stderr,
                    )
                    pd.init_from_lines(pd_lines)
                    if self.verbose > 3:
                        log.debug("Got PD:\n%s", pp(pd.as_dict(True)))
                pd_lines = []
                pd_nr = None
                pd_enc = None
                pd_slot = None
                continue

            # Check for PD Enclosure
            match = re_pd_enc.search(line)
            if match:
                pd_enc = int(match.group(1))
                continue

            # Checkfor PD slot
            match = re_pd_slot.search(line)
            if match:
                pd_slot = int(match.group(1))
                continue

            pd_lines.append(line)

        if pd:
            self.pds.append(pd)
        if pd_lines and pd_enc is not None and pd_slot is not None:
            if self.verbose > 2:
                log.debug("Init of PD [%d:%d] of LD %d.",
                        pd_enc, pd_slot, self.number)
            pd = MegaraidPd(
                    adapter = self.adapter,
                    enclosure = pd_enc,
                    slot = pd_slot,
                    appname = self.appname,
                    verbose  = self.verbose,
                    base_dir = self.base_dir,
                    use_stderr = self.use_stderr,
            )
            pd.init_from_lines(pd_lines)
            if self.verbose > 3:
                log.debug("Got PD:\n%s", pp(pd.as_dict(True)))
            self.pds.append(pd)

        self.initialized = True

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
