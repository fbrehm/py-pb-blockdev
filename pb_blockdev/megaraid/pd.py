#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the MegaraidPd class
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
from pb_blockdev.megaraid import MegaraidPdError

__version__ = '0.3.4'

log = logging.getLogger(__name__)

# Device Id: 51
re_device_id = re.compile(r'^Device\s+Id\s*:\s*(\d+)', re.IGNORECASE)

# Drive's position: DiskGroup: 4, Span: 0, Arm: 0
re_disk_group = re.compile(r"^Drive's\s+position\s*:\s+DiskGroup\s*:\s+(\d+),\s+Span\s*:\s+(\d+),\s+Arm\s*:\s+(\d+)",
        re.IGNORECASE)

# WWN: 5000C50056337998
re_wwn = re.compile(r'^WWN\s*:\s*(?:0x)?([\da-f]+)', re.IGNORECASE)

# PD Type: SAS
re_pd_type = re.compile(r'^PD\s+Type\s*:\s*(\S+.*)', re.IGNORECASE)

# Hotspare Information:
re_hotspare = re.compile(r'^Hotspare\s+Information\s*:', re.IGNORECASE)

# Sector Size:  512
re_sector_size = re.compile(r'^Sector\s+Size\s*:\s*(\d+)', re.IGNORECASE)

# Raw Size: 2.728 TB [0x15d50a3b0 Sectors]
re_raw_sectors = re.compile(r'^Raw\s+Size\s*:.*\[(?:0x)?([\da-f]+)\s+Sectors\]',
        re.IGNORECASE)

# Coerced Size: 2.728 TB [0x15d400000 Sectors]
re_coerced_sectors = re.compile(r'^Coerced\s+Size\s*:.*\[(?:0x)?([\da-f]+)\s+Sectors\]',
        re.IGNORECASE)

# Media Error Count: 0
re_media_errors = re.compile(r'^Media\s+Error\s+Count\s*:\s*(\d+)',
        re.IGNORECASE)

# Other Error Count: 0
re_other_errors = re.compile(r'^Other\s+Error\s+Count\s*:\s*(\d+)',
        re.IGNORECASE)

# Predictive Failure Count: 0
re_predictive_failures = re.compile(r'^Predictive\s+Failure\s+Count\s*:\s*(\d+)',
        re.IGNORECASE)

# Firmware state: Online, Spun Up
re_firmware_state = re.compile(r'^Firmware\s+state\s*:\s*(\S+.*)',
        re.IGNORECASE)

# Foreign State: None
re_foreign_state = re.compile(r'^Foreign\s+state\s*:\s*(\S+.*)', re.IGNORECASE)

# SAS Address(0): 0x500304800058338c
re_sas_address = re.compile(r'^SAS\s+Address\s*\(\s*\d+\s*\)\s*:\s*(?:0x)?([\da-f]+)',
        re.IGNORECASE)

# Inquiry Data: CVCV3053035K060AGN  INTEL SSDSC2CW060A3                     400i
re_inq_data = re.compile(r'^Inquiry\s+Data\s*:\s*(\S+.*)', re.IGNORECASE)

# CVCV3053035K060AGN  INTEL SSDSC2CW060A3                     400i
re_inc_intel = re.compile(r'^(\S+)\s+INTEL\s+(\S+)', re.IGNORECASE)

re_inc_wd = re.compile(r'^WD-(\S+)\s+(\S+)', re.IGNORECASE)

# SEAGATE ST33000650SS    0004Z296KT81
re_inq_seagate1 = re.compile(r'^SEAGATE\s+(\S+)\s+(\S+)', re.IGNORECASE)

# Z1Y06K0TST3000NM0033-9ZM178                     0001
re_inq_seagate2 = re.compile(r'(\S{8})(ST\S+)(?:\s.*)?$', re.IGNORECASE)

#==============================================================================
class MegaraidPd(PbBaseObject):
    """
    Encapsulation class for for a Megaraid Physical drive (PD)
    """

    #------------------------------------------------------------
    def __init__(self,
            adapter,
            enclosure,
            slot,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            ):
        """
        Initialisation of the megaraid Physical drive object.

        @param adapter: the Id of the Megaraid adapter
        @type adapter: int
        @param enclosure: the Id of the enclosure on the Megaraid adapter
        @type enclosure: int
        @param slot: the slot Id in the enclosure
        @type slot: int
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
        self._enclosure = int(enclosure)
        self._slot = int(slot)

        super(MegaraidPd, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
        )

        self._device_id = None
        self._disk_group = None
        self._is_hotspare = False
        self._wwn = None
        self._type = None
        self._sector_size = 512
        self._raw_sectors = None
        self._coerced_sectors = None
        self._media_errors = None
        self._other_errors = None
        self._predictive_failures = None
        self._firmware_state = None
        self._foreign_state = None
        self._inq_data = None
        self._vendor = None
        self._model = None
        self._serial = None

        self.sas_addresses = []

        self.initialized = True

    #------------------------------------------------------------
    @property
    def adapter(self):
        """The Id of the Megaraid controller."""
        return self._adapter

    #------------------------------------------------------------
    @property
    def enclosure(self):
        """The Id of the enclosure."""
        return self._enclosure

    #------------------------------------------------------------
    @property
    def slot(self):
        """The slot of the PD in the enclosure."""
        return self._slot

    #------------------------------------------------------------
    @property
    def device_name(self):
        """The name of the device in the '$Enclosure:$slot' form."""
        return "%d:%d" % (self.enclosure, self.slot)

    #------------------------------------------------------------
    @property
    def device_id(self):
        """The device ID of the PD on the adapter."""
        return self._device_id

    @device_id.setter
    def device_id(self, value):
        if value is None:
            self._device_id = None
            return
        self._device_id = int(value)
        return

    #------------------------------------------------------------
    @property
    def disk_group(self):
        """
        Information, in which disk groups == logical devices the
        physical device is used. It's a tuple of three integer value, which
        are describing the disk group, the span and the arm (whatever this is).
        """
        return self._disk_group

    #------------------------------------------------------------
    @property
    def wwn(self):
        """
        The World Wide Name (WWN) or World Wide Identifier (WWID) of the
        physical device as a long integer value, if known, otherwise None.
        """
        return self._wwn

    #------------------------------------------------------------
    @property
    def wwn_hex(self):
        """
        The World Wide Name (WWN) or World Wide Identifier (WWID) of the
        physical device as a hex number as string, if known, otherwise None.
        """
        if self._wwn is None:
            return None
        return "%016x" % (self._wwn)

    #------------------------------------------------------------
    @property
    def type(self):
        """
        The type of the physical device - SAS or SATA or what else.
        """
        return self._type

    #------------------------------------------------------------
    @property
    def is_hotspare(self):
        """Flag, that the current PD is used as a hotspare."""
        return self._is_hotspare

    #------------------------------------------------------------
    @property
    def sector_size(self):
        """The sector size of the PD in Bytes."""
        return self._sector_size

    @sector_size.setter
    def sector_size(self, value):
        self._sector_size = int(value)
        return

    #------------------------------------------------------------
    @property
    def raw_sectors(self):
        """The raw number of sectors of the disk, how delivered from vendor."""
        return self._raw_sectors

    #------------------------------------------------------------
    @property
    def raw_size(self):
        """
        The raw size of the disk, how delivered from vendor, in Bytes
        as a long value.
        """
        if self.sector_size is None or self.raw_sectors is None:
            return None
        if sys.version_info[0] <= 2:
            return long(self.sector_size) * long(self.raw_sectors)
        return self.sector_size * self.raw_sectors

    #------------------------------------------------------------
    @property
    def raw_size_mb(self):
        """
        The raw size of the disk, how delivered from vendor, in MiBytes
        as an integer value.
        """
        if self.raw_size is None:
            return None
        return int(self.raw_size / 1024 / 1024)

    #------------------------------------------------------------
    @property
    def raw_size_gb(self):
        """
        The raw size of the disk, how delivered from vendor, in GiBytes
        as a float value.
        """
        if self.raw_size is None:
            return None
        return float(self.raw_size) / 1024.0 / 1024.0 / 1024.0

    #------------------------------------------------------------
    @property
    def coerced_sectors(self):
        """The number of sectors of the disk, how used by MegaRaid."""
        return self._coerced_sectors

    #------------------------------------------------------------
    @property
    def coerced_size(self):
        """
        The size of the disk, how used by MegaRaid, in Bytes
        as a long value.
        """
        if self.sector_size is None or self.coerced_sectors is None:
            return None
        if sys.version_info[0] <= 2:
            return long(self.sector_size) * long(self.coerced_sectors)
        return self.sector_size * self.coerced_sectors

    #------------------------------------------------------------
    @property
    def coerced_size_mb(self):
        """
        The size of the disk, how used by MegaRaid, in MiBytes
        as an integer value.
        """
        if self.coerced_size is None:
            return None
        return int(self.coerced_size / 1024 / 1024)

    #------------------------------------------------------------
    @property
    def coerced_size_gb(self):
        """
        The size of the disk, how used by MegaRaid, in GiBytes
        as a float value.
        """
        if self.coerced_size is None:
            return None
        return float(self.coerced_size) / 1024.0 / 1024.0 / 1024.0

    #------------------------------------------------------------
    @property
    def sectors(self):
        """The number of sectors of the disk, how used by MegaRaid.
            Is equal to self.coerced_sectors."""
        return self.coerced_sectors

    #------------------------------------------------------------
    @property
    def size(self):
        """
        The size of the disk, how used by MegaRaid, in Bytes
        as a long value. Is equal to self.coerced_size.
        """
        return self.coerced_size

    #------------------------------------------------------------
    @property
    def size_mb(self):
        """
        The size of the disk, how used by MegaRaid, in MiBytes
        as an integer value. Is equal to self.coerced_size_mb.
        """
        return self.coerced_size_mb

    #------------------------------------------------------------
    @property
    def size_gb(self):
        """
        The size of the disk, how used by MegaRaid, in GiBytes
        as a float value. Is equal to self.coerced_size_gb.
        """
        return self.coerced_size_gb

    #------------------------------------------------------------
    @property
    def media_errors(self):
        """The number of media errors of this physical disk."""
        return self._media_errors

    #------------------------------------------------------------
    @property
    def other_errors(self):
        """The number of other errors of this physical disk."""
        return self._other_errors

    #------------------------------------------------------------
    @property
    def predictive_failures(self):
        """The number of predictive failures of this physical disk."""
        return self._predictive_failures

    #------------------------------------------------------------
    @property
    def firmware_state(self):
        """The current state of the firmware of this physical disk."""
        return self._firmware_state

    #------------------------------------------------------------
    @property
    def foreign_state(self):
        """
        The current state of a foreign configuration of this physical disk.
        Note: 'None' is the good state!
        """
        return self._foreign_state

    #------------------------------------------------------------
    @property
    def inq_data(self):
        """The inquiry data of the disk."""
        return self._inq_data

    #------------------------------------------------------------
    @property
    def vendor(self):
        """The vendor how interpreted from inquiry data of the disk."""
        return self._vendor

    #------------------------------------------------------------
    @property
    def model(self):
        """The model how interpreted from inquiry data of the disk."""
        return self._model

    #------------------------------------------------------------
    @property
    def serial(self):
        """The serial number how interpreted from inquiry data of the disk."""
        return self._serial

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MegaraidPd, self).as_dict(short = short)
        res['adapter'] = self.adapter
        res['enclosure'] = self.enclosure
        res['slot'] = self.slot
        res['device_name'] = self.device_name
        res['device_id'] = self.device_id
        res['disk_group'] = self.disk_group
        res['wwn'] = self.wwn
        res['wwn_hex'] = self.wwn_hex
        res['type'] = self.type
        res['is_hotspare'] = self.is_hotspare
        res['sector_size'] = self.sector_size
        res['sectors'] = self.sectors
        res['size'] = self.size
        res['size_mb'] = self.size_mb
        res['size_gb'] = self.size_gb
        res['raw_sectors'] = self.raw_sectors
        res['raw_size'] = self.raw_size
        res['raw_size_mb'] = self.raw_size_mb
        res['raw_size_gb'] = self.raw_size_gb
        res['coerced_sectors'] = self.coerced_sectors
        res['coerced_size'] = self.coerced_size
        res['coerced_size_mb'] = self.coerced_size_mb
        res['coerced_size_gb'] = self.coerced_size_gb
        res['media_errors'] = self.media_errors
        res['other_errors'] = self.other_errors
        res['predictive_failures'] = self.predictive_failures
        res['firmware_state'] = self.firmware_state
        res['inq_data'] = self.inq_data
        res['vendor'] = self.vendor
        res['model'] = self.model
        res['serial'] = self.serial

        return res

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("adapter=%r" % (self.adapter))
        fields.append("enclosure=%r" % (self.enclosure))
        fields.append("slot=%r" % (self.slot))
        if self.device_id is not None:
            fields.append("device_id=%r" % (self.device_id))
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

        if not isinstance(other, MegaraidPd):
            msg = "Comparision partner %r is not a MegaraidPd object." % (other)
            raise ValueError(msg)

        res = cmp(self.adapter, other.adapter)
        if res != 0:
            return res

        res = cmp(self.enclosure, other.enclosure)
        if res != 0:
            return res

        return cmp(self.slot, other.slot)

    #--------------------------------------------------------------------------
    def init_from_lines(self, lines):
        """
        Init of all properties from output lines from 'MegaCLI -pdInfo'.
        """

#        The Output looks like:
#
#            Enclosure Device ID: 9
#            Slot Number: 8
#            Drive's position: DiskGroup: 4, Span: 0, Arm: 0
#            Enclosure position: 1
#            Device Id: 14
#            WWN: 5000C50056337998
#            Sequence Number: 2
#            Media Error Count: 0
#            Other Error Count: 0
#            Predictive Failure Count: 0
#            Last Predictive Failure Event Seq Number: 0
#            PD Type: SAS
#
#            Raw Size: 2.728 TB [0x15d50a3b0 Sectors]
#            Non Coerced Size: 2.728 TB [0x15d40a3b0 Sectors]
#            Coerced Size: 2.728 TB [0x15d400000 Sectors]
#            Sector Size:  512
#            Logical Sector Size:  512
#            Physical Sector Size:  512
#            Firmware state: Online, Spun Up
#            Commissioned Spare : No
#            Emergency Spare : No
#            Device Firmware Level: 0004
#            Shield Counter: 0
#            Successful diagnostics completion on :  N/A
#            SAS Address(0): 0x5000c50056337999
#            SAS Address(1): 0x0
#            Connected Port Number: 0(path0)
#            Inquiry Data: SEAGATE ST33000650SS    0004Z296Q3B9
#            FDE Capable: Not Capable
#            FDE Enable: Disable
#            Secured: Unsecured
#            Locked: Unlocked
#            Needs EKM Attention: No
#            Foreign State: None
#            Device Speed: 6.0Gb/s
#            Link Speed: 6.0Gb/s
#            Media Type: Hard Disk Device
#            Drive:  Not Certified
#            Drive Temperature :38C (100.40 F)
#            PI Eligibility:  No
#            Drive is formatted for PI information:  No
#            PI: No PI
#            Port-0 :
#            Port status: Active
#            Port's Linkspeed: 6.0Gb/s
#            Port-1 :
#            Port status: Active
#            Port's Linkspeed: 6.0Gb/s
#            Drive has flagged a S.M.A.R.T alert : No
#
#
#        or
#
#            Enclosure Device ID: 9
#            Slot Number: 19
#            Enclosure position: 1
#            Device Id: 51
#            WWN: 5000C5005591A4E0
#            Sequence Number: 2
#            Media Error Count: 0
#            Other Error Count: 0
#            Predictive Failure Count: 0
#            Last Predictive Failure Event Seq Number: 0
#            PD Type: SAS
#            Hotspare Information:
#            Type: Dedicated, is revertible
#            Array #: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
#            Raw Size: 2.728 TB [0x15d50a3b0 Sectors]
#            Non Coerced Size: 2.728 TB [0x15d40a3b0 Sectors]
#            Coerced Size: 2.728 TB [0x15d400000 Sectors]
#            Sector Size:  512
#            Logical Sector Size:  512
#            Physical Sector Size:  512
#            Firmware state: Hotspare, Spun down
#            Device Firmware Level: 0004
#            Shield Counter: 0
#            Successful diagnostics completion on :  N/A
#            SAS Address(0): 0x5000c5005591a4e1
#            SAS Address(1): 0x0
#            Connected Port Number: 0(path0)
#            Inquiry Data: SEAGATE ST33000650SS    0004Z2951AYB
#            FDE Capable: Not Capable
#            FDE Enable: Disable
#            Secured: Unsecured
#            Locked: Unlocked
#            Needs EKM Attention: No
#            Foreign State: None
#            Device Speed: 6.0Gb/s
#            Link Speed: 6.0Gb/s
#            Media Type: Hard Disk Device
#            Drive:  Not Certified
#            Drive Temperature : N/A
#            PI Eligibility:  No
#            Drive is formatted for PI information:  No
#            PI: No PI
#            Port-0 :
#            Port status: Active
#            Port's Linkspeed: 6.0Gb/s
#            Port-1 :
#            Port status: Active
#            Port's Linkspeed: 6.0Gb/s
#            Drive has flagged a S.M.A.R.T alert : No

        if isinstance(lines, basestring):
            lines = lines.splitlines()

        self.initialized = False

        self.device_id = None
        self._disk_group = None
        self._wwn = None
        self._type = None
        self._is_hotspare = False
        self.sector_size = 512
        self._raw_sectors = None
        self._coerced_sectors = None
        self._media_errors = None
        self._other_errors = None
        self._predictive_failures = None
        self._firmware_state = None
        self._foreign_state = None
        self._inq_data = None
        self._vendor = None
        self._model = None
        self._serial = None

        self.sas_addresses = []

        if self.verbose > 3:
            log.debug("Analyzing lines:\n%s", pp(lines))

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Checking for Device Id
            match = re_device_id.search(line)
            if match:
                self.device_id = match.group(1)
                if self.verbose > 3:
                    log.debug("Device-Id of [%s]: %d.",
                            self.device_name, self.device_id)
                continue

            # Checking for disk position
            match = re_disk_group.search(line)
            if match:
                self._disk_group = (
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                )
                continue

            # Checking for WWN
            match = re_wwn.search(line)
            if match:
                if sys.version_info[0] <= 2:
                    self._wwn = long(match.group(1), 16)
                else:
                    self._wwn = int(match.group(1), 16)
                continue

            # Checking for PD type
            match = re_pd_type.search(line)
            if match:
                self._type = match.group(1)
                continue

            # Checking for hotspare information
            if re_hotspare.search(line):
                self._is_hotspare = True
                continue

            # Checking for sector size
            match = re_sector_size.search(line)
            if match:
                self.sector_size = match.group(1)
                continue

            # Checking for Raw Size:
            match = re_raw_sectors.search(line)
            if match:
                self._raw_sectors = int(match.group(1), 16)
                continue

            # Checking for Coerced Size:
            match = re_coerced_sectors.search(line)
            if match:
                self._coerced_sectors = int(match.group(1), 16)
                continue

            # Checking for Media errors
            match = re_media_errors.search(line)
            if match:
                self._media_errors = int(match.group(1))
                continue

            # Checking for Other errors
            match = re_other_errors.search(line)
            if match:
                self._other_errors = int(match.group(1))
                continue

            # Checking for Predictive Failures
            match = re_predictive_failures.search(line)
            if match:
                self._predictive_failures = int(match.group(1))
                continue

            # Checking for the Firmware state
            match = re_firmware_state.search(line)
            if match:
                self._firmware_state = match.group(1)
                continue

            # Checking for the Foreign state
            match = re_foreign_state.search(line)
            if match:
                self._foreign_state = match.group(1)
                continue

            # Checking for a SAS address
            match = re_sas_address.search(line)
            if match:
                addr = int(match.group(1), 16)
                self.sas_addresses.append(addr)
                continue

            # Checking for the inqury data
            match = re_inq_data.search(line)
            if match:
                self._inq_data = match.group(1)
                if self.inq_data:
                    self.analyze_inq_data(self.inq_data)
                continue

        self.initialized = True

    #--------------------------------------------------------------------------
    def analyze_inq_data(self, inq_data):
        """
        Analyzing the inquiry data and put the results, if some found, in
        self.vendor, self.model and self.serial.
        """

        self._vendor = None
        self._model = None
        self._serial = None

        match = re_inc_intel.search(inq_data)
        if match:
            self._vendor = 'Intel'
            self._model = match.group(2)
            self._serial = match.group(1)
            return

        match = re_inc_wd.search(inq_data)
        if match:
            self._vendor = 'WD'
            self._model = match.group(1)
            self._serial = match.group(2)
            return

        match = re_inq_seagate1.search(inq_data)
        if match:
            self._vendor = 'Seagate'
            self._model = match.group(1)
            self._serial = match.group(2)
            return

        match = re_inq_seagate2.search(inq_data)
        if match:
            self._vendor = 'Seagate'
            self._model = match.group(2)
            self._serial = match.group(1)
            return

        log.warn("Could't interprete inquiry data %r.", inq_data)
        return

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
