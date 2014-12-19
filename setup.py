#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from distutils.core import setup, Command

# own modules:
cur_dir = os.getcwd()
if sys.argv[0] != '' and sys.argv[0] != '-c':
    cur_dir = os.path.dirname(sys.argv[0])

libdir = os.path.join(cur_dir, 'pb_blockdev')
if os.path.exists(libdir) and os.path.isdir(libdir):
    sys.path.insert(0, os.path.abspath(cur_dir))
del libdir
del cur_dir

import pb_blockdev

packet_version = pb_blockdev.__version__

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'pb-blockdev',
    version = packet_version,
    description = 'ProfitBricks modules for wrapper classes of different block devices.',
    long_description = read('README.txt'),
    author = 'Frank Brehm',
    author_email = 'frank.brehm@profitbricks.com',
    url = 'ssh://git.profitbricks.localdomain/srv/git/python/pb-blockdev.git',
    license = 'LGPLv3+',
    platforms = ['posix'],
    packages = [
        'pb_blockdev',
        'pb_blockdev.md',
        'pb_blockdev.megaraid',
        'pb_blockdev.multipath',
    ],
    scripts = [
#        'bin/megaraid-lds',
#        'bin/megaraid-pds',
    ],
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    requires = [
        'pb_base (>= 0.3.10)',
    ]
)




#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
