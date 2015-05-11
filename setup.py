#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
from distutils.core import setup
import datetime

# own modules:
cur_dir = os.getcwd()
if sys.argv[0] != '' and sys.argv[0] != '-c':
    cur_dir = os.path.dirname(sys.argv[0])

libdir = os.path.join(cur_dir, 'pb_blockdev')
if os.path.exists(libdir) and os.path.isdir(libdir):
    sys.path.insert(0, os.path.abspath(cur_dir))

import pb_blockdev

packet_version = pb_blockdev.__version__


packet_name = 'pb_blockdev'
debian_pkg_name = 'pb-blockdev'

__author__ = 'Frank Brehm'
__contact__ = 'frank.brehm@profitbricks.com'
__copyright__ = '(C) 2010 - 2015 by ProfitBricks GmbH, Berlin'
__license__ = 'LGPL3+'
__desc__ = ('ProfitBricks modules for wrapper classes of different '
    'block devices under Linux.')


# -----------------------------------
def read(fname):
    content = None
    print("Reading %r ..." % (fname))
    if sys.version_info[0] > 2:
        with open(fname, 'r', encoding = 'utf-8') as fh:
            content = fh.read()
    else:
        with open(fname, 'r') as fh:
            content = fh.read()
    return content


# -----------------------------------
debian_dir = os.path.join(cur_dir, 'debian')
changelog_file = os.path.join(debian_dir, 'changelog')
readme_file = os.path.join(cur_dir, 'README.txt')


# -----------------------------------
def get_debian_version():
    if not os.path.isfile(changelog_file):
        return None
    changelog = read(changelog_file)
    first_row = changelog.splitlines()[0].strip()
    if not first_row:
        return None
    pattern = r'^' + re.escape(debian_pkg_name) + r'\s+\(([^\)]+)\)'
    match = re.search(pattern, first_row)
    if not match:
        return None
    return match.group(1).strip()

debian_version = get_debian_version()
if debian_version is not None and debian_version != '':
    packet_version = debian_version

# -----------------------------------
local_version_file = os.path.join(libdir, 'local_version.py')
local_version_file_content = '''\
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: %s
@contact: %s
@copyright: © 2010 - %d by %s, Berlin
@summary: %s
"""

__author__ = '%s <%s>'
__copyright__ = '(C) 2010 - %d by profitbricks.com'
__contact__ = %r
__version__ = %r
__license__ = %r

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
'''


# -----------------------------------
def write_local_version():

    cur_year = datetime.date.today().year
    content = local_version_file_content % (
        __author__, __contact__, cur_year, __author__, __desc__, __author__,
        __contact__, cur_year, __contact__, packet_version, __license__)
    # print(content)

    print("Writing %r ..." % (local_version_file))
    fh = None
    try:
        if sys.version_info[0] > 2:
            fh = open(local_version_file, 'wt', encoding='utf-8')
        else:
            fh = open(local_version_file, 'wt')
        fh.write(content)
    finally:
        if fh:
            fh.close

# Write lib/storage_tools/local_version.py
write_local_version()


# -----------------------------------
setup(
    name='pb-blockdev',
    version=packet_version,
    description=__desc__,
    long_description=read('README.txt'),
    author=__author__,
    author_email=__contact__,
    url="https://gitlab.pb.local/dcops/pb-blockdev",
    license='LGPLv3+',
    platforms=['posix'],
    packages=[
        'pb_blockdev',
        'pb_blockdev.lvm',
        'pb_blockdev.md',
        'pb_blockdev.megaraid',
        'pb_blockdev.multipath',
    ],
    scripts=[],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    requires=[
        'pb_base (>= 0.6.0)',
    ]
)

# =======================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
