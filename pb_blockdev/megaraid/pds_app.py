#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the megaraid-pds application
"""

# Standard modules
import sys
import logging

# Third party modules

# Own modules
from pb_base.common import pp

from pb_base.app import PbApplication

from pb_base.handler import CommandNotFoundError

import pb_blockdev.megaraid

from pb_blockdev.megaraid.handler import MegaraidHandler

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.3.5'

log = logging.getLogger(__name__)


# =============================================================================
class MegaraidPdsApp(PbApplication):
    """
    Application class for the 'megaraid-pds' application.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, verbose=0, version=pb_blockdev.__version__,
            *arg, **kwargs):
        """
        Initialisation of the megaraid-pds application object.
        """

        self.handler = None
        """
        @ivar: a handler object to execute MegaCLI commands
        @type: MegaraidHandler
        """

        indent = ' ' * self.usage_term_len

        usage = "%(prog)s [General options]"
        usage += '\n'
        usage += indent + "%(prog)s -h|--help\n"
        usage += indent + "%(prog)s -V|--version"

        desc = "List of all physical drives of all MegaRaid adapters"

        self.parsable = False
        """
        @ivar: Output of found physical disks in a parsable format (CSV)
        @type: bool
        """

        super(MegaraidPdsApp, self).__init__(
            usage=usage,
            verbose=verbose,
            version=version,
            description=desc,
            *arg, **kwargs
        )

        self.post_init()

        try:
            self.handler = MegaraidHandler(
                appname=self.appname,
                verbose=self.verbose,
                base_dir=self.base_dir,
            )
        except CommandNotFoundError as e:
            sys.stderr.write(str(e) + "\n\n")
            sys.exit(5)

        self.initialized = True

    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        """
        Method to initiate the argument parser.
        """

        super(MegaraidPdsApp, self).init_arg_parser()

        self.arg_parser.add_argument(
            '-P', '--parsable',
            action='store_true',
            dest='parsable',
            help=(
                'Output of found physical disks in a parsable format (CSV), '
                'without headers and footers'),
        )

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):
        """
        Execute some actions after parsing the command line parameters.
        """

        super(MegaraidPdsApp, self).perform_arg_parser()

        self.parsable = self.args.parsable

    # -------------------------------------------------------------------------
    def _run(self):
        """The underlaying startpoint of the application."""

        count_adapters = self.handler.adapter_count()
        if not count_adapters:
            sys.stderr.write("No MegaRaid controllers found.\n\n")
            sys.exit(1)

        line_templ = "%2d  %3d  %4d  %11d  %10.f  %-68s  %s"
        inq_templ = "%-8s %-20s %s"
        if self.parsable:
            line_templ = "%d;%d;%d;%d;%1.f;%s;%s"
            inq_templ = "%s %s %s"
        else:
            print (
                "Adp. Enc. Slot    Size MiB    Size GiB  Vendor   "
                "Model                "
                "Serial                                  Firmware state")

        size_total = 0

        adapter_id = 0
        while adapter_id < count_adapters:
            enclosures = self.handler.get_enclosures(adapter_id)
            if self.verbose > 2:
                if enclosures:
                    encs = []
                    for enclosure in enclosures:
                        encs.append(enclosure.as_dict(True))
                    log.debug("Got enclosures:\n%s", pp(encs))

            for enc in sorted(enclosures):
                if not enc.nr_pds:
                    continue
                slot = 0
                first = True
                while slot < enc.nr_slots:
                    pd = self.handler.get_pd(adapter_id, enc.id, slot)
                    if not pd:
                        slot += 1
                        continue
                    if self.verbose > 2 and first:
                        log.debug("Got physical device:\n%s", pp(pd.as_dict(True)))
                        first = False

                    inq_data = pd.inq_data
                    if pd.vendor:
                        inq_data = inq_templ % (pd.vendor, pd.model, pd.serial)

                    if pd.size:
                        size_total += pd.size

                    print line_templ % (
                        adapter_id, enc.id, slot, pd.size_mb,
                        pd.size_gb, inq_data, pd.firmware_state)

                    slot += 1

            adapter_id += 1

        size_mb = int(size_total / 1024 / 1024)
        size_gb = float(size_total) / 1024.0 / 1024.0 / 1024.0

        if not self.parsable:
            print "\n%-13s  %11d  %10.f" % ('Total:', size_mb, size_gb)

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
