#!/bin/bash

set -u
set -e

pot_file="py_pb_blockdev.pot"
output_dir="po"
pkg_version="0.3.5"
pkg_name="profitbricks-python-blockdevice"
src_dir="pb_blockdev"

cd $(dirname $0)

if [ ! -d po ] ; then
    echo "Creating directory 'po' ..."
    mkdir po
fi

xgettext --output="${pot_file}" \
        --output-dir="${output_dir}" \
        --language="Python" \
        --add-comments \
        --keyword=_ \
        --keyword=__ \
        --force-po \
        --indent \
        --add-location \
        --width=85 \
        --sort-by-file \
        --package-name="${pkg_name}" \
        --package-version="${pkg_version}" \
        --msgid-bugs-address=frank.brehm@profitbricks.com \
        $(find "${src_dir}" -type f -name '*.py' | sort)

sed -i -e 's/msgid[ 	][ 	]*"/msgid "/' \
       -e 's/msgstr[ 	][ 	]*"/msgstr "/' \
       -e 's/^        /      /' \
       "${output_dir}/${pot_file}"

# vim: ts=4 et
