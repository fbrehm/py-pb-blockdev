#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the handler class for all megaraid operations
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

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_blockdev.megaraid import MegaraidLdError
from pb_blockdev.megaraid import MegaraidEnclosureError

from pb_blockdev.megaraid.ld import MegaraidLogicalDrive

from pb_blockdev.megaraid.enc import MegaraidEnclosure

from pb_blockdev.megaraid.pd import MegaraidPd

from pb_blockdev.translate import translator

_ = translator.lgettext
__ = translator.lngettext

__version__ = '0.7.0'

log = logging.getLogger(__name__)

re_exit_code = re.compile(r'^\s*Exit\s+Code\s*:\s*(?:0x)?([\da-f]+)',
        re.IGNORECASE | re.MULTILINE)
re_adp_count = re.compile(r'^\s*Controller\s+Count\s*:\s+(\d+)\.',
        re.IGNORECASE | re.MULTILINE)

# Adapter 0: Device at Enclosure - 8, Slot - 24 is not found.
re_slot_empty = re.compile(r'Device\s+at\s+Enclosure.*is\s+not\s+found.',
        re.IGNORECASE)

# Virtual Drive: 0 (Target Id: 0)
start_ld_pattern = r'^(?:\S.*\s)?Virtual\s+Drive\s*:\s+(\d+)'
start_ld_pattern += r'(?:\s*\(\s*Target\s+Id\s*:\s*(\d+)\s*\))\s*$'
re_start_ld = re.compile(start_ld_pattern, re.IGNORECASE)
del start_ld_pattern

# Adapter 0: Virtual Drive 77 Does not Exist.
re_ld_not_exists = re.compile((r'^\s*(Adapter\s+\d+\s*:\s*' +
            r'Virtual\s+Drive\s+\d+\s+Does\s+not\s+Exist.*)'),
            re.IGNORECASE | re.MULTILINE)

#==============================================================================
class MegaraidHandler(PbBaseHandler):
    """
    Handler class for executing MegaCLI commands.
    """

    #------------------------------------------------------------
    def __init__(self,
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
        Initialisation of the megaraid handler object.

        @raise CommandNotFoundError: if the MegaCLI command could not be found.

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

        self._megacli = None
        """
        @ivar: The absolute path to the MegaCLI command.
        @type: str
        """

        super(MegaraidHandler, self).__init__(
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

        self._init_megacli()

        self.initialized = True

    #------------------------------------------------------------
    @property
    def megacli(self):
        """The absolute path to the MegaCLI command."""
        return self._megacli

    #--------------------------------------------------------------------------
    def as_dict(self, short = False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(MegaraidHandler, self).as_dict(short = short)
        res['megacli'] = self.megacli

        return res

    #--------------------------------------------------------------------------
    def _init_megacli(self):
        """
        Searches in path for the MegaCLI command and set self.megacli
        with the found path.

        @raise CommandNotFoundError: if the MegaCLI could not be found

        """

        if self.verbose > 2:
            log.debug(_("Searching for the MegaCLI command ..."))

        paths = caller_search_path()
        add_paths = (
            os.sep + os.path.join('opt', 'MegaRAID', 'MegaCli'),
            os.sep + os.path.join('opt', 'lsi', 'megacli'),
            os.sep + os.path.join('opt', 'megacli'),
        )
        for d in add_paths:
            if os.path.isdir(d) and not d in paths:
                paths.append(d)

        if self.verbose > 3:
            log.debug(_("Searching command in paths:") + "\n" + pp(paths))

        commands = ('MegaCli64', 'MegaCli', 'megacli')
        for cmd in commands:
            found = False
            for d in paths:
                if self.verbose > 3:
                    log.debug(_("Searching command %(cmd)r in %(dir)r ...") % {
                            'cmd': cmd, 'dir': d})
                p = os.path.join(d, cmd)
                if os.path.exists(p):
                    if self.verbose > 2:
                        log.debug(_("Found %r ..."), p)
                    if os.access(p, os.X_OK):
                        self._megacli = p
                        return
                    else:
                        log.debug(_("File %r is not executable."), p)

        raise CommandNotFoundError('MegaCli')

    #--------------------------------------------------------------------------
    def exec_megacli(self, args, nolog = True):
        """
        Executes the MegaCli command with the given arguments.

        @raise CommandNotFoundError: if the MegaCli command could not be found.

        @param args: the arguments for calling MegaCli
        @type args: str or list of str
        @param nolog: executes MegaCli with the '-NoLog' option
        @type nolog: bool

        @return: a dictionary with the following keys:
            * out - the output from STDOUT
            * err - the output from SRDERR
            * retval - the return value from OS
            * exitcode - the Exit Code from inside the output of MegaCli
        @retval: dict

        """

        if not self.megacli:
            raise CommandNotFoundError('MegaCli')

        cmd = [self.megacli]

        if isinstance(args, basestring):
            cmd.append(args)
        else:
            for arg in args:
                cmd.append(arg)

        if nolog:
            cmd.append('-NoLog')

        (ret, stdoutdata, stderrdata) = self.call(cmd, quiet = True)

        result = {
            'out': stdoutdata,
            'err': stderrdata,
            'retval': ret,
            'exitcode': None,
        }

        match = re_exit_code.search(stdoutdata)
        if match:
            ec = match.group(1)
            result['exitcode'] = int(ec, 16)

        return result

    #--------------------------------------------------------------------------
    def adapter_count(self, nolog = True):
        """
        Executes 'MegaCLI -adpCount' and returns the number of found
        MegaRaid adapters.

        @raise CommandNotFoundError: if the MegaCli command could not be found.
        @raise MegaraidHandlerError: if the number of adapters could not detect
                                     in output of MegaCli

        @param nolog: executes MegaCli with the '-NoLog' option
        @type nolog: bool

        @return: the number of found MegaRaid adapters.
        @rtype: int

        """

        log.debug(_("Retrieving number of MegaRaid controllers ..."))
        result = self.exec_megacli('-adpCount', nolog)

        # NOTE: the command 'MegaCLI -adpCount' returns an exit value of 1,
        #       if an adapter was found (no idea what happens, if more
        #       adapters are found).

        count = None
        match = re_adp_count.search(result['out'])
        if match:
            count = int(match.group(1))
        else:
            msg = _("Could not detect number of MegaRaid controllers in output of %r.") % (
                    'MegaCLI -adpCount')
            raise MegaraidHandlerError(msg)

        if self.verbose > 1:
            msg = __("Found %d MegaRaid controller.",
                    "Found %d MegaRaid controllers.", count) % (count)

        return count

    #--------------------------------------------------------------------------
    def get_pd(self, adapter_id, enc_id, slot, nolog = True):
        """
        Executes 'MegaCLI -pdInfo ...' for a particular physical device.

        @raise CommandNotFoundError: if the MegaCli command could not be found.
        @raise MegaraidHandlerError: if the output of 'MegaCLI -pdInfo' could
                                     not analyzed.

        @param adapter_id: the numeric ID of the MegaRaid adapter
        @type adapter_id: int
        @param enc_id: the numeric enclosure Id
        @type enc_id: int
        @param slot: the numeric slot number of the PD in the enclosure
        @type slot: int
        @param nolog: executes MegaCli with the '-NoLog' option
        @type nolog: bool

        @return: the found physical device or None, if nothing was found.
        @rtype: MegaraidPd or None

        """

        adapter_id = int(adapter_id)
        enc_id = int(enc_id)
        slot = int(slot)

        pd_name = "%d:%d" % (enc_id, slot)

        log.debug(_("Retrieving data of physical drive [%(pd)s] on MegaRaid controller %(a)d ...") % {
                'pd': pd_name, 'a': adapter_id})
        args = [
            '-pdInfo',
            ('-PhysDrv[%s]' % (pd_name)),
            ('-a%d' % (adapter_id)),
        ]
        result = self.exec_megacli(args, nolog)

        if re_slot_empty.search(result['out']):
            log.debug(_("PD [%(pd)s] (adapter %(a)d) doesn't exists.") % {
                    'pd': pd_name, 'a': adapter_id})
            return None

        pd = MegaraidPd(
                adapter = adapter_id,
                enclosure = enc_id,
                slot = slot,
                appname = self.appname,
                verbose  = self.verbose,
                base_dir = self.base_dir,
                use_stderr = self.use_stderr,
        )

        pd.init_from_lines(result['out'])

        return pd

    #--------------------------------------------------------------------------
    def get_enclosures(self, adapter_id, nolog = True):
        """
        Executes 'MegaCLI -EncInfo' and returns a list of found enclosures
        connected with the given MegaRaid adapter.

        @raise CommandNotFoundError: if the MegaCli command could not be found.
        @raise MegaraidHandlerError: if the output of 'MegaCLI -EncInfo' could
                                     not analyzed.

        @param adapter_id: the numeric ID of the MegaRaid adapter
        @type adapter_id: int
        @param nolog: executes MegaCli with the '-NoLog' option
        @type nolog: bool

        @return: all found enclosures
        @rtype: list of MegaraidEnclosure

        """

        adapter_id = int(adapter_id)
        enclosures = []
        log.debug(_("Retrieving enclosures connected with MegaRaid controller %d ..."),
                adapter_id)
        args = [
            '-EncInfo',
            ('-a%d' % (adapter_id)),
        ]
        result = self.exec_megacli(args, nolog)

        re_start_enc = re.compile(r'^Enclosure\s+(\d+)\s*:$', re.IGNORECASE)

        if self.verbose > 3:
            log.debug(_("Got:"))
            sys.stderr.write(result['out'])

        # Defaults for enclosure ...
        enc_nr = None
        enclosure = None
        lines = []

        for line in result['out'].splitlines():

            line = line.strip()
            if not line:
                continue

            match = re_start_enc.search(line)
            if match:
                enc_nr = int(match.group(1))
                if self.verbose > 2:
                    log.debug(_("Starting with new enclosure No %d."), enc_nr)

                # New defaults for enclosure ...
                if enclosure:
                    if lines:
                        enclosure.init_from_lines(lines)
                    enclosures.append(enclosure)
                enclosure = MegaraidEnclosure(
                    adapter = adapter_id,
                    number = enc_nr,
                    appname = self.appname,
                    verbose  = self.verbose,
                    base_dir = self.base_dir,
                    use_stderr = self.use_stderr,
                )
                lines = []

                continue

            lines.append(line)

        if enclosure:
            if lines:
                enclosure.init_from_lines(lines)
            enclosures.append(enclosure)

        return enclosures

    #--------------------------------------------------------------------------
    def get_all_lds(self, adapter_id, nolog = True):
        """
        Executes 'MegaCLI -LdPdInfo' and returns a list of found logical drives
        of the given MegaRaid adapter.

        @raise CommandNotFoundError: if the MegaCli command could not be found.
        @raise MegaraidHandlerError: if the output of 'MegaCLI -LdPdInfo' could
                                     not analyzed.

        @param adapter_id: the numeric ID of the MegaRaid adapter
        @type adapter_id: int
        @param nolog: executes MegaCli with the '-NoLog' option
        @type nolog: bool

        @return: all found logical drives
        @rtype: list of MegaraidLogicalDrive

        """

        adapter_id = int(adapter_id)
        lds = []
        log.debug(_("Retrieving logical drives of MegaRaid controller %d ..."),
                adapter_id)
        args = [
            '-LdPdInfo',
            ('-a%d' % (adapter_id)),
        ]
        result = self.exec_megacli(args, nolog)

        # Virtual Drive: 0 (Target Id: 0)
        re_start_ld = re.compile(r'^(?:\S.*\s)?Virtual\s+Drive\s*:\s+(\d+)(?:\s*\(\s*Target\s+Id\s*:\s*(\d+)\s*\))\s*$',
                re.IGNORECASE)

        if self.verbose > 4:
            log.debug(_("Got:"))
            sys.stderr.write(result['out'])

        # Defaults for ld ...
        ld_nr = None
        target_id = None
        ld = None
        lines = []

        for line in result['out'].splitlines():

            line = line.strip()
            if not line:
                continue

            match = re_start_ld.search(line)
            if match:
                ld_nr = int(match.group(1))
                if match.group(2) is not None:
                    target_id = int(match.group(2))
                if self.verbose > 2:
                    log.debug(_("Starting with new LD %(ld)r (target Id %(tid)r).") % {
                            'ld': ld_nr, 'tid': target_id})

                # New defaults for LD ...
                if ld:
                    if lines:
                        ld.init_from_lines(lines)
                    lds.append(ld)
                ld = MegaraidLogicalDrive(
                    adapter = adapter_id,
                    number = ld_nr,
                    target_id = target_id,
                    appname = self.appname,
                    verbose  = self.verbose,
                    base_dir = self.base_dir,
                    use_stderr = self.use_stderr,
                )
                lines = []
                target_id = None

                continue

            lines.append(line)

        if ld:
            if lines:
                ld.init_from_lines(lines)
            lds.append(ld)

        return lds

    #--------------------------------------------------------------------------
    def get_ld_info(self, adapter_id, ld_nr, ld = None, nolog = True):
        """
        Executes 'MegaCLI -LdInfo -LX' and returns the logical drive
        of the given MegaRaid adapter.

        @raise CommandNotFoundError: if the MegaCli command could not be found.
        @raise MegaraidHandlerError: if the output of 'MegaCLI -LdInfo' could
                                     not analyzed.
        @raise ValueError: on wrong parameters

        @param adapter_id: the numeric ID of the MegaRaid adapter
        @type adapter_id: int
        @param ld_nr: the number of the logical drive on the MegaRaid adapter
        @type ld_nr: int
        @param ld: a MegaraidLogicalDrive, which should completed
        @type ld: MegaraidLogicalDrive or None
        @param nolog: executes MegaCli with the '-NoLog' option
        @type nolog: bool

        @return: the found logical drive, or None, if not found
        @rtype: MegaraidLogicalDrive or None

        """

        adapter_id = int(adapter_id)
        ld_nr = int(ld_nr)
        if ld is not None:
            if not isinstance(ld, MegaraidLogicalDrive):
                msg = _("Parameter %(lbl)r %(val)r is not a %(cls)s object.") % {
                        'lbl': 'ld', 'val': ld, 'cls': 'MegaraidLogicalDrive'}
                raise ValueError(msg)

        no_override = False
        if ld:
            no_override = True
        else:
            ld = MegaraidLogicalDrive(
                    adapter = adapter_id,
                    number = ld_nr,
                    target_id = target_id,
                    appname = self.appname,
                    verbose  = self.verbose,
                    base_dir = self.base_dir,
                    use_stderr = self.use_stderr,
            )

        log.debug(_("Retrieving infos about logical drive %(ld)d of MegaRaid controller %(adp)d ...") % {
                 'ld': ld_nr, 'adp': adapter_id})
        args = [
            '-LdInfo',
            ('-L%d' % (ld_nr)),
            ('-a%d' % (adapter_id)),
        ]
        result = self.exec_megacli(args, nolog)

        if self.verbose > 4:
            log.debug(_("Got:"))
            sys.stderr.write(result['out'])

        match = re_ld_not_exists.search(result['out'])
        if match:
            log.warn(match.group(1))
            return None

        lines = []
        for line in result['out'].splitlines():
            line = line.strip()
            if not line:
                continue
            lines.append(line)

        ld.init_from_lines(lines, no_override)

        if self.verbose > 3:
            log.debug((_("%s object:") % ('MegaraidLogicalDrive')) + "\n" +
                    pp(ld.as_dict(True)))

        return ld

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
