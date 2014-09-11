#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the MegaraidEnclosure class
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
from pb_blockdev.megaraid import MegaraidEnclosureError

from pb_blockdev.translate import translator

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.5.0'

log = logging.getLogger(__name__)

#==============================================================================
class VoltageSensor(PbBaseObject):
    """
    Encapsulation class for a Voltage sensor
    """

    #------------------------------------------------------------
    def __init__(self,
            number,
            status = None,
            voltage = None,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            ):
        """
        Initialisation of the Voltage sensor object.

        @param number: the running number of the voltage sensor
        @type number: int
        @param status: the textual status of the voltage sensor
        @type status: str
        @param voltage: the current voltage in Volt
        @type voltage: float
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

        self._number = int(number)
        self._status = None
        if status is not None:
            self._status = str(status).strip()
        self._voltage = None

        super(VoltageSensor, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
        )

        if voltage is not None:
            self.voltage = voltage

    #------------------------------------------------------------
    @property
    def number(self):
        """The running number of the voltage sensor."""
        return self._number

    #------------------------------------------------------------
    @property
    def status(self):
        """The textual status of the voltage sensor."""
        return self._status

    @status.setter
    def status(self, value):
        if value is None:
            self._status = None
            return
        self._status = str(value).strip()

    #------------------------------------------------------------
    @property
    def voltage(self):
        """The current voltage in Volt."""
        return self._voltage

    @voltage.setter
    def voltage(self, value):
        if value is None:
            self._voltage = None
            return
        self._voltage = float(value)
        return

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(VoltageSensor, self).as_dict(short = short)
        res['number'] = self.number
        res['status'] = self.status
        res['voltage'] = self.voltage

        return res

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("number=%r" % (self.number))
        if self.status is not None:
            fields.append("status=%r" % (self.status))
        if self.voltage is not None:
            fields.append("voltage=%r" % (self.voltage))
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

        if not isinstance(other, VoltageSensor):
            msg = _("Comparision partner %(p)r is not a %(o)s object.") % {
                    'p': other, 'o': 'VoltageSensor'}
            raise ValueError(msg)

        return cmp(self.number, other.number)

#==============================================================================
class FanStatus(PbBaseObject):
    """
    Encapsulation class for a fan status
    """

    #------------------------------------------------------------
    def __init__(self,
            number,
            status = None,
            speed = None,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            ):
        """
        Initialisation of the fan status object.

        @param number: the running number of the fan status
        @type number: int
        @param status: the textual status of the fan status
        @type status: str
        @param speed: the current speed of the fan
        @type voltage: str
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

        self._number = int(number)
        self._status = None
        if status is not None:
            self._status = str(status).strip()
        self._speed = None

        super(FanStatus, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
        )

        if speed is not None:
            self.speed = speed

    #------------------------------------------------------------
    @property
    def number(self):
        """The running number of the fan status."""
        return self._number

    #------------------------------------------------------------
    @property
    def status(self):
        """The textual status of the fan status."""
        return self._status

    @status.setter
    def status(self, value):
        if value is None:
            self._status = None
            return
        self._status = str(value).strip()
        return

    #------------------------------------------------------------
    @property
    def speed(self):
        """The current speed of the fan."""
        return self._speed

    @speed.setter
    def speed(self, value):
        if value is None:
            self._speed = None
            return
        self._speed = str(value).strip()
        return

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(FanStatus, self).as_dict(short = short)
        res['number'] = self.number
        res['status'] = self.status
        res['speed'] = self.speed

        return res

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("number=%r" % (self.number))
        if self.status is not None:
            fields.append("status=%r" % (self.status))
        if self.speed is not None:
            fields.append("speed=%r" % (self.speed))
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

        if not isinstance(other, FanStatus):
            msg = _("Comparision partner %(p)r is not a %(o)s object.") % {
                    'p': other, 'o': 'FanStatus'}
            raise ValueError(msg)

        return cmp(self.number, other.number)

#==============================================================================
class TemperatureSensor(PbBaseObject):
    """
    Encapsulation class for a Temperature sensor
    """

    #------------------------------------------------------------
    def __init__(self,
            number,
            status = None,
            temperature = None,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            ):
        """
        Initialisation of the Temperature sensor object.

        @param number: the running number of the Temperature sensor
        @type number: int
        @param status: the textual status of the Temperature sensor
        @type status: str
        @param temperature: the current temperature in degree Celsius
        @type temperature: int
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

        self._number = int(number)
        self._status = None
        if status is not None:
            self._status = str(status).strip()
        self._temperature = None

        super(TemperatureSensor, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
        )

        if temperature is not None:
            self.temperature = temperature

    #------------------------------------------------------------
    @property
    def number(self):
        """The running number of the temperature sensor."""
        return self._number

    #------------------------------------------------------------
    @property
    def status(self):
        """The textual status of the temperature sensor."""
        return self._status

    @status.setter
    def status(self, value):
        if value is None:
            self._status = None
            return
        self._status = str(value).strip()

    #------------------------------------------------------------
    @property
    def temperature(self):
        """The current temperature in degree Celsius."""
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        if value is None:
            self._temperature = None
            return
        self._temperature = int(value)
        return

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(TemperatureSensor, self).as_dict(short = short)
        res['number'] = self.number
        res['status'] = self.status
        res['temperature'] = self.temperature

        return res

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("number=%r" % (self.number))
        if self.status is not None:
            fields.append("status=%r" % (self.status))
        if self.temperature is not None:
            fields.append("temperature=%r" % (self.temperature))
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

        if not isinstance(other, TemperatureSensor):
            msg = _("Comparision partner %(p)r is not a %(o)s object.") % {
                    'p': other, 'o': 'TemperatureSensor'}
            raise ValueError(msg)

        return cmp(self.number, other.number)

#==============================================================================
class MegaraidEnclosure(PbBaseObject):
    """
    Encapsulation class for a Megaraid Enclosure
    """

    #------------------------------------------------------------
    def __init__(self,
            adapter,
            number,
            id = None,
            appname = None,
            verbose = 0,
            version = __version__,
            base_dir = None,
            use_stderr = False,
            ):
        """
        Initialisation of the megaraid enclosure object.

        @param adapter: the Id of the Megaraid controller
        @type adapter: int
        @param number: the running number of the enclosure on the Megaraid controller
        @type number: int
        @param id: the enclosure Id
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
        self._id = None
        if id is not None:
            self._id = int(id)

        super(MegaraidEnclosure, self).__init__(
                appname = appname,
                verbose = verbose,
                version = version,
                base_dir = base_dir,
                use_stderr = use_stderr,
                initialized = False,
        )

        self._nr_slots = None
        self._nr_power_supplies = None
        self._nr_fans = None
        self._nr_temp_sensors = None
        self._nr_alarms = None
        self._nr_pds = None
        self._nr_voltage_sensors = None

        self._status = None
        self._connector_name = None
        self._enc_type = None
        self._vendor = None
        self._product_name = None
        self._product_revision = None
        self._vendor_specific = None

        self.voltage_sensors = []
        """
        @ivar: all voltage sensors of this enclosure
        @type: list of VoltageSensor
        """

        self.fans = []
        """
        @ivar: all known fans of the enclosure
        @type: list of FanStatus
        """

        self.temperature_sensors = []
        """
        @ivar: all temperature sensors of this enclosure
        @type: list of TemperatureSensor
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
        """The running number of the enclosure on the Megaraid controller."""
        return self._number

    #------------------------------------------------------------
    @property
    def id(self):
        """The enclosure Id."""
        return self._id

    @id.setter
    def id(self, value):
        eid = int(value)
        if eid < 0:
            raise ValueError(_("The enclosure Id must be a positive integer value."))
        self._id = eid

    #------------------------------------------------------------
    @property
    def nr_slots(self):
        """The number of drive slots in the enclosure."""
        return self._nr_slots

    #------------------------------------------------------------
    @property
    def nr_power_supplies(self):
        """The number of power supplies in the enclosure."""
        return self._nr_power_supplies

    #------------------------------------------------------------
    @property
    def nr_fans(self):
        """The number of fans in the enclosure."""
        return self._nr_fans

    #------------------------------------------------------------
    @property
    def nr_temp_sensors(self):
        """The number of temperature sensors in the enclosure."""
        return self._nr_temp_sensors

    #------------------------------------------------------------
    @property
    def nr_alarms(self):
        """The number of alarms originated from the enclosure."""
        return self._nr_alarms

    #------------------------------------------------------------
    @property
    def nr_pds(self):
        """The number of mounted physical drives in the enclosure."""
        return self._nr_pds

    #------------------------------------------------------------
    @property
    def nr_voltage_sensors(self):
        """The number of voltage sensors in the enclosure."""
        return self._nr_voltage_sensors

    #------------------------------------------------------------
    @property
    def status(self):
        """The textual state of the enclosure."""
        return self._status

    #------------------------------------------------------------
    @property
    def connector_name(self):
        """The name of the enclosure connector."""
        return self._connector_name

    #------------------------------------------------------------
    @property
    def enc_type(self):
        """The type of the enclosure."""
        return self._enc_type

    #------------------------------------------------------------
    @property
    def vendor(self):
        """The vendor name of the enclosure."""
        return self._vendor

    #------------------------------------------------------------
    @property
    def product_name(self):
        """The product name of the enclosure."""
        return self._product_name

    #------------------------------------------------------------
    @property
    def product_revision(self):
        """The product revision of the enclosure."""
        return self._product_revision

    #------------------------------------------------------------
    @property
    def vendor_specific(self):
        """The vendor specific product name of the enclosure."""
        return self._vendor_specific

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MegaraidEnclosure, self).as_dict(short = short)
        res['adapter'] = self.adapter
        res['number'] = self.number
        res['id'] = self.id
        res['nr_slots'] = self.nr_slots
        res['nr_power_supplies'] = self.nr_power_supplies
        res['nr_fans'] = self.nr_fans
        res['nr_temp_sensors'] = self.nr_temp_sensors
        res['nr_alarms'] = self.nr_alarms
        res['nr_pds'] = self.nr_pds
        res['nr_voltage_sensors'] = self.nr_voltage_sensors
        res['status'] = self.status
        res['connector_name'] = self.connector_name
        res['enc_type'] = self.enc_type
        res['vendor'] = self.vendor
        res['product_name'] = self.product_name
        res['product_revision'] = self.product_revision
        res['vendor_specific'] = self.vendor_specific

        res['voltage_sensors'] = []
        for vs in self.voltage_sensors:
            res['voltage_sensors'].append(vs.as_dict(short = short))

        res['fans'] = []
        for fs in self.fans:
            res['fans'].append(fs.as_dict(short = short))

        res['temperature_sensors'] = []
        for ts in self.temperature_sensors:
            res['temperature_sensors'].append(ts.as_dict(short = short))

        return res

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("adapter=%r" % (self.adapter))
        fields.append("number=%r" % (self.number))
        if self.id is not None:
            fields.append("id=%r" % (self.id))
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

        if not isinstance(other, MegaraidEnclosure):
            msg = _("Comparision partner %(p)r is not a %(o)s object.") % {
                    'p': other, 'o': 'MegaraidEnclosure'}
            raise ValueError(msg)

        res = cmp(self.adapter, other.adapter)
        if res != 0:
            return res

        return cmp(self.number, other.number)

    #--------------------------------------------------------------------------
    def init_from_lines(self, lines):
        """
        Init of all properties from output lines from 'MegaCLI -EncInfo'.
        """

#        The Output looks like:
#
#            Number of enclosures on adapter 0 -- 3
#
#            Enclosure 0:
#            Device ID                     : 8
#            Number of Slots               : 12
#            Number of Power Supplies      : 0
#            Number of Fans                : 3
#            Number of Temperature Sensors : 1
#            Number of Alarms              : 0
#            Number of SIM Modules         : 0
#            Number of Physical Drives     : 12
#            Status                        : Normal
#            Position                      : 1
#            Connector Name                : Port 4 - 7
#            Enclosure type                : SES
#            FRU Part Number               : N/A
#            Enclosure Serial Number       : N/A
#            ESM Serial Number             : N/A
#            Enclosure Zoning Mode         : N/A
#            Partner Device Id             : 65535
#
#            Inquiry data                  :
#                Vendor Identification     : LSI
#                Product Identification    : SAS2X28
#                Product Revision Level    : 0e0b
#                Vendor Specific           : x36-55.14.11.0
#
#        Number of Voltage Sensors         :2
#
#        Voltage Sensor                    :0
#        Voltage Sensor Status             :OK
#        Voltage Value                     :5010 milli volts
#
#        Voltage Sensor                    :1
#        Voltage Sensor Status             :OK
#        Voltage Value                     :11810 milli volts
#
#        Number of Power Supplies     : 0
#
#        Number of Fans               : 3
#
#        Fan                          : 0
#        Fan Status                   : OK
#
#        Fan                          : 1
#        Fan Speed              :Medium Speed
#        Fan Status                   : OK
#
#        Fan                          : 2
#        Fan Status                   : OK
#
#        Number of Temperature Sensors : 1
#
#        Temp Sensor                  : 0
#        Temperature                  : 28
#        Temperature Sensor Status    : OK
#
#        Number of Chassis             : 1
#
#        Chassis                      : 0
#        Chassis Status               : OK
#
#            Enclosure 1:
#            Device ID                     : 9
#            Number of Slots               : 24
#            Number of Power Supplies      : 0
#            Number of Fans                : 5
#                    Number of Temperature Sensors : 1
#            Number of Alarms              : 0
#            Number of SIM Modules         : 0
#            Number of Physical Drives     : 24
#            Status                        : Normal
#            Position                      : 1
#            Connector Name                : Port 0 - 3
#            Enclosure type                : SES
#            FRU Part Number               : N/A
#            Enclosure Serial Number       : N/A
#            ESM Serial Number             : N/A
#            Enclosure Zoning Mode         : N/A
#            Partner Device Id             : 65535
#
#            Inquiry data                  :
#                Vendor Identification     : LSI
#                Product Identification    : SAS2X36
#                Product Revision Level    : 0e0b
#                Vendor Specific           : x36-55.14.11.0
#
#        Number of Voltage Sensors         :2
#
#        Voltage Sensor                    :0
#        Voltage Sensor Status             :OK
#        Voltage Value                     :4980 milli volts
#
#        Voltage Sensor                    :1
#        Voltage Sensor Status             :OK
#        Voltage Value                     :11910 milli volts
#
#        Number of Power Supplies     : 0
#
#        Number of Fans               : 5
#
#        Fan                          : 0
#        Fan Status                   : OK
#
#        Fan                          : 1
#        Fan Status                   : OK
#
#        Fan                          : 2
#        Fan Speed              :Medium Speed
#        Fan Status                   : OK
#
#        Fan                          : 3
#        Fan Status                   : Not Available
#
#        Fan                          : 4
#        Fan Status                   : Not Available
#
#        Number of Temperature Sensors : 1
#
#        Temp Sensor                  : 0
#        Temperature                  : 32
#        Temperature Sensor Status    : OK
#
#        Number of Chassis             : 1
#
#        Chassis                      : 0
#        Chassis Status               : OK
#
#            Enclosure 2:
#            Device ID                     : 252
#            Number of Slots               : 8
#            Number of Power Supplies      : 0
#            Number of Fans                : 0
#            Number of Temperature Sensors : 0
#            Number of Alarms              : 0
#            Number of SIM Modules         : 1
#            Number of Physical Drives     : 0
#            Status                        : Normal
#            Position                      : 1
#            Connector Name                : Unavailable
#            Enclosure type                : SGPIO
#            FRU Part Number               : N/A
#            Enclosure Serial Number       : N/A
#            ESM Serial Number             : N/A
#            Enclosure Zoning Mode         : N/A
#            Partner Device Id             : Unavailable
#
#            Inquiry data                  :
#                Vendor Identification     : LSI
#                Product Identification    : SGPIO
#                Product Revision Level    : N/A
#                Vendor Specific           :
#
#
#        Exit Code: 0x00

        self.initialized = False

        if self.verbose > 3:
            log.debug(_("Analyzing lines:") + "\n" + pp(lines))

        self._id = None
        self._nr_slots = None
        self._nr_power_supplies = None
        self._nr_fans = None
        self._nr_temp_sensors = None
        self._nr_alarms = None
        self._nr_pds = None
        self._nr_voltage_sensors = None

        self._status = None
        self._connector_name = None
        self._enc_type = None
        self._vendor = None
        self._product_name = None
        self._product_revision = None
        self._vendor_specific = None

        self.voltage_sensors = []
        cur_voltage_sensor = None

        self.fans = []
        cur_fan_status = None

        self.temperature_sensors = []
        cur_temperature_sensor = None

        re_enc_id = re.compile(r'^Device\s+ID\s*:\s*(\d+)', re.IGNORECASE)
        re_nr_slots = re.compile(r'^Number\s+of\s+Slots\s*:\s*(\d+)', re.IGNORECASE)
        re_nr_power_supplies = re.compile(r'^Number\s+of\s+Power\s+Supplies\s*:\s*(\d+)',
                re.IGNORECASE)
        re_nr_fans = re.compile(r'^Number\s+of\s+Fans\s*:\s*(\d+)', re.IGNORECASE)
        re_nr_temp_sensors = re.compile(r'^Number\s+of\s+Temperature\s+Sensors\s*:\s*(\d+)',
                re.IGNORECASE)
        re_nr_alarms = re.compile(r'^Number\s+of\s+Alarms\s*:\s*(\d+)', re.IGNORECASE)
        re_nr_pds = re.compile(r'^Number\s+of\s+Physical\s+Drives\s*:\s*(\d+)',
                re.IGNORECASE)
        re_nr_voltage_sensors = re.compile(r'^Number\s+of\s+Voltage\s+Sensors\s*:\s*(\d+)',
                re.IGNORECASE)

        re_status = re.compile(r'^Status\s*:\s*(\S+.*)', re.IGNORECASE)
        re_connector_name = re.compile(r'^Connector\s+Name\s*:\s*(\S+.*)',
                re.IGNORECASE)
        re_enc_type = re.compile(r'^Enclosure\s+type\s*:\s*(\S+.*)',
                re.IGNORECASE)
        re_vendor = re.compile(r'^Vendor\s+Identification\s*:\s*(\S+.*)',
                re.IGNORECASE)
        re_product_name = re.compile(r'^Product\s+Identification\s*:\s*(\S+.*)',
                re.IGNORECASE)
        re_product_revision = re.compile(r'^Product\s+Revision\s+Level\s*:\s*(\S+.*)',
                re.IGNORECASE)
        re_vendor_specific = re.compile(r'^Vendor\s+Specific\s*:\s*(\S+.*)',
                re.IGNORECASE)

        re_voltage_sensor = re.compile(r'^Voltage\s+Sensor\s*:\s*(\d+)',
                re.IGNORECASE)
        re_voltage_sensor_status = re.compile(r'^Voltage\s+Sensor\s+Status\s*:\s*(\S+.*)',
                re.IGNORECASE)
        re_voltage_value = re.compile(r'^Voltage\s+Value\s*:\s*(\d+(?:\.\d*)?)\s*(milli)?\s*volt',
                re.IGNORECASE)

        re_fan = re.compile(r'^Fan\s*:\s*(\d+)', re.IGNORECASE)
        re_fan_status = re.compile(r'^Fan\s+Status\s*:\s*(\S+.*)', re.IGNORECASE)
        re_fan_speed = re.compile(r'^Fan\s+Speed\s*:\s*(\S+.*)', re.IGNORECASE)

        re_temp_sensor = re.compile(r'^Temp\s+Sensor\s*:\s*(\d+)', re.IGNORECASE)
        re_temperature = re.compile(r'^Temperature\s*:\s*(\d+)', re.IGNORECASE)
        re_temp_status = re.compile(r'^Temperature\s+Sensor\s+Status\s*:\s*(\S+.*)',
                re.IGNORECASE)

        re_not_avail = re.compile(r'^Not\s+Available', re.IGNORECASE)

        for line in lines:

            # Checking for Device Id
            match = re_enc_id.search(line)
            if match:
                self.id = match.group(1)
                if self.verbose > 2:
                    log.debug(_("Id of enclosure No %(enc)d: %(id)d.") % {
                            'enc': self.number, 'id': self.id})
                continue

            # Checking for the number of slots
            match = re_nr_slots.search(line)
            if match:
                self._nr_slots = int(match.group(1))
                continue

            # Checking for the number of power supplies
            match = re_nr_power_supplies.search(line)
            if match:
                self._nr_power_supplies = int(match.group(1))
                continue

            # Checking for the number of fans
            match = re_nr_fans.search(line)
            if match:
                self._nr_fans = int(match.group(1))
                continue

            # Checking for the number of Temperature Sensors
            match = re_nr_temp_sensors.search(line)
            if match:
                self._nr_temp_sensors = int(match.group(1))
                continue

            # Checking for the number of alarms
            match = re_nr_alarms.search(line)
            if match:
                self._nr_alarms = int(match.group(1))
                continue

            # Checking for the number of mounted physical drives
            match = re_nr_pds.search(line)
            if match:
                self._nr_pds = int(match.group(1))
                continue

            # Checking for the number of voltage sensors
            match = re_nr_voltage_sensors.search(line)
            if match:
                self._nr_voltage_sensors = int(match.group(1))
                continue

            # Checking for the state
            match = re_status.search(line)
            if match:
                if match.group(1).lower() != 'n/a':
                    self._status = match.group(1)
                continue

            # Checking for the connector name
            match = re_connector_name.search(line)
            if match:
                if match.group(1).lower() != 'n/a':
                    self._connector_name = match.group(1)
                continue

            # Checking for the enclosure type
            match = re_enc_type.search(line)
            if match:
                if match.group(1).lower() != 'n/a':
                    self._enc_type = match.group(1)
                continue

            # Checking for the vendor name
            match = re_vendor.search(line)
            if match:
                if match.group(1).lower() != 'n/a':
                    self._vendor = match.group(1)
                continue

            # Checking for the product name
            match = re_product_name.search(line)
            if match:
                if match.group(1).lower() != 'n/a':
                    self._product_name = match.group(1)
                continue

            # Checking for the product revision
            match = re_product_revision.search(line)
            if match:
                if match.group(1).lower() != 'n/a':
                    self._product_revision = match.group(1)
                continue

            # Checking for the vendore specific product name
            match = re_vendor_specific.search(line)
            if match:
                if match.group(1).lower() != 'n/a':
                    self._vendor_specific = match.group(1)
                continue

            # Check for start of a voltage sensor
            match = re_voltage_sensor.search(line)
            if match:
                if cur_voltage_sensor:
                    self.voltage_sensors.append(cur_voltage_sensor)
                nr = int(match.group(1))
                if self.verbose > 3:
                    log.debug(_("Found voltage sensor %d."), nr)
                cur_voltage_sensor = VoltageSensor(
                        nr,
                        appname = self.appname,
                        verbose = self.verbose,
                        base_dir = self.base_dir,
                        use_stderr = self.use_stderr,
                )

            # Check for the voltage sensor status
            match = re_voltage_sensor_status.search(line)
            if match:
                st = match.group(1)
                if self.verbose > 3:
                    log.debug(_("Found voltage sensor status %r."), st)
                if cur_voltage_sensor:
                    cur_voltage_sensor.status = st
                continue

            # Check for the voltage sensor value
            match = re_voltage_value.search(line)
            if match:
                value = float(match.group(1))
                if match.group(2):
                    value /= 1000.0
                if self.verbose > 3:
                    log.debug(_("Found voltage sensor value %f."), value)
                if cur_voltage_sensor:
                    cur_voltage_sensor.voltage = value
                continue

            # Check for start of a fan status
            match = re_fan.search(line)
            if match:
                if cur_fan_status:
                    self.fans.append(cur_fan_status)
                nr = int(match.group(1))
                if self.verbose > 3:
                    log.debug(_("Found Fan %d."), nr)
                cur_fan_status = FanStatus(
                        nr,
                        appname = self.appname,
                        verbose = self.verbose,
                        base_dir = self.base_dir,
                        use_stderr = self.use_stderr,
                )

            # Check for the fan status
            match = re_fan_status.search(line)
            if match:
                st = match.group(1)
                if re_not_avail.search(st):
                    continue
                if self.verbose > 3:
                    log.debug(_("Found fan status %r."), st)
                if cur_fan_status:
                    cur_fan_status.status = st
                continue

            # Check for the fan speed
            match = re_fan_speed.search(line)
            if match:
                value = match.group(1)
                if self.verbose > 3:
                    log.debug(_("Found fan speed %r."), value)
                if cur_fan_status:
                    cur_fan_status.speed = value
                continue

            # Check for start of a temperature sensor
            match = re_temp_sensor.search(line)
            if match:
                if cur_temperature_sensor:
                    self.temperature_sensors.append(cur_temperature_sensor)
                nr = int(match.group(1))
                if self.verbose > 3:
                    log.debug(_("Found temperature sensor %d."), nr)
                cur_temperature_sensor = TemperatureSensor(
                        nr,
                        appname = self.appname,
                        verbose = self.verbose,
                        base_dir = self.base_dir,
                        use_stderr = self.use_stderr,
                )

            # Check for the temperature sensor status
            match = re_temp_status.search(line)
            if match:
                st = match.group(1)
                if self.verbose > 3:
                    log.debug(_("Found temperature sensor status %r."), st)
                if cur_temperature_sensor:
                    cur_temperature_sensor.status = st
                continue

            # Check for the temperature value
            match = re_temperature.search(line)
            if match:
                value = int(match.group(1))
                if self.verbose > 3:
                    log.debug(_("Found temperature value %d."), value)
                if cur_temperature_sensor:
                    cur_temperature_sensor.temperature = value
                continue

        if cur_voltage_sensor:
            self.voltage_sensors.append(cur_voltage_sensor)
        if cur_fan_status:
            self.fans.append(cur_fan_status)
        if cur_temperature_sensor:
            self.temperature_sensors.append(cur_temperature_sensor)
        self.initialized = True


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
