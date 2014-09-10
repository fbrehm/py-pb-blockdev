#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, ProfitBricks GmbH, Berlin
@summary: The module for the megaraid-lds application
"""

# Standard modules
import sys
import os
import logging

# Third party modules
import argparse

# Own modules
import pb_base
from pb_base.common import pp, to_unicode_or_bust, to_utf8_or_bust

from pb_base.errors import PbError

from pb_base.object import PbBaseObjectError

from pb_base.app import PbApplicationError
from pb_base.app import PbApplication

from pb_base.handler import CommandNotFoundError

import pb_blockdev.megaraid

from pb_blockdev.megaraid import MegaraidError
from pb_blockdev.megaraid import MegaraidHandlerError

from pb_blockdev.megaraid.handler import MegaraidHandler

__version__ = '0.3.3'

log = logging.getLogger(__name__)

#==============================================================================
class MegaraidLdsApp(PbApplication):
    """
    Application class for the 'megaraid-lds' application.
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            verbose = 0,
            version = pb_blockdev.__version__,
            *arg, **kwargs):
        """
        Initialisation of the megaraid-lds application object.
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

        desc = "List of all logical drives of all MegaRaid adapters"

        self.parsable = False
        """
        @ivar: Output of found logical disks in a parsable format (CSV)
        @type: bool
        """

        self.hotspares = False
        """
        @ivar: retrieve the assigned hotspares and display them
        @type: bool
        """

        super(MegaraidLdsApp, self).__init__(
                usage = usage,
                verbose = verbose,
                version = version,
                description = desc,
                *arg, **kwargs
        )

        self.post_init()

        try:
            self.handler = MegaraidHandler(
                    appname = self.appname,
                    verbose = self.verbose,
                    base_dir = self.base_dir,
            )
        except CommandNotFoundError, e:
            sys.stderr.write(str(e) + "\n\n")
            sys.exit(5)

        self.initialized = True

    #--------------------------------------------------------------------------
    def init_arg_parser(self):
        """
        Method to initiate the argument parser.
        """

        super(MegaraidLdsApp, self).init_arg_parser()

        self.arg_parser.add_argument(
            '-P', '--parsable',
            action = 'store_true',
            dest = 'parsable',
            help = ('Output of found logical disks in a parsable format (CSV), ' +
                    'without headers and footers'),
        )

        self.arg_parser.add_argument(
            '-H', '--hotspares',
            action = 'store_true',
            dest = 'hotspares',
            help = 'Retrieve the assigned hotspares and display them.',
        )

    #--------------------------------------------------------------------------
    def perform_arg_parser(self):
        """
        Execute some actions after parsing the command line parameters.
        """

        super(MegaraidLdsApp, self).perform_arg_parser()

        self.parsable = self.args.parsable
        self.hotspares = self.args.hotspares

    #--------------------------------------------------------------------------
    def _run(self):
        """The underlaying startpoint of the application."""

        count_adapters = self.handler.adapter_count()
        if not count_adapters:
            sys.stderr.write("No MegaRaid controllers found.\n\n")
            sys.exit(1)

        if self.parsable:
            line_templ = "%d;%d;%s;%s;%s;%s"

        line_templ = "%(adp)3s %(id)3s    %(lvl)-15s %(size)10s   %(cache)-15s   %(pds)s"
        if self.parsable:
            line_templ = "%(adp)s;%(id)s;%(lvl)s;%(size)s;%(cache)s;%(pds)s"
        else:
            info = {}
            info['adp'] = 'Adp'
            info['id'] = 'Id'
            info['lvl'] = 'RAID level'
            info['size'] = 'Size'
            info['cache'] = "Cache"
            info['pds'] = 'PDs'
            print line_templ % info

        size_total = 0
        all_lds = []

        adapter_id = 0
        while adapter_id < count_adapters:

            lds = self.handler.get_all_lds(adapter_id)
            if self.verbose > 3:
                if lds:
                    ldlist = []
                    for ld in lds:
                        ldlist.append(ld.as_dict(True))
                    log.debug("Got logical drives:\n%s", pp(ldlist))

            if lds:
                for ld in lds:
                    all_lds.append(ld)

            adapter_id += 1

        for ld in sorted(all_lds):

            if ld.cached:
                ld = self.handler.get_ld_info(ld.adapter, ld.number, ld)

            info = {}
            info['adp'] = ld.adapter
            info['id'] = ld.number
            info['lvl'] = ld.raid_level
            info['size'] = ld.size
            info['cache'] = "no cache"
            if ld.cached:
                if ld.cache_rw:
                    info['cache'] = 'cache r/w'
                else:
                    info['cache'] = 'cache ro'
            elif ld.is_cachecade_drive:
                info['cache'] = "CacheCade drive"
            pds = []
            info['pds'] = ''
            for pd in ld.pds:
                pds.append("%d:%d" % (pd.enclosure, pd.slot))
            if pds:
                if self.parsable:
                    info['pds'] = ','.join(pds)
                else:
                    info['pds'] = ', '.join(pds)


            print line_templ % info

            adapter_id += 1

        size_mb = int(size_total / 1024 / 1024)
        size_gb = float(size_total) / 1024.0 / 1024.0 / 1024.0

        if not self.parsable and size_total:
            print "\n%-13s  %11d  %10.f" % ('Total:', size_mb, size_gb)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
