#!/usr/bin/env python2.7
"""
Generate adj.mk.

Usage: mk_adj.py <root-dir> <strip-prefix>

Arguments:
    root-dir: The directory from which to start searching.
    strip-prefix: The prefix to strip from each path in the output fragment.
"""

import os
import sys
import re
from collections import OrderedDict, defaultdict

class UnknownInterpreterError(Exception): pass


# Decides if the first line of a file looks like a shebang and groups
# the interpreter path for later inspection
SHEBANG_PATTERN = re.compile("#\s*!\s*(\S+)")
ENV_SHEBANG_PATTERN = re.compile("#\s*!\s*\S*\/env\s+(\S+)")

# XXX use basenames to better match interpreters
KNOWN_INTERPRETERS = [
    # Allowed hard-coded paths
    ("/bin/ksh", None),
    ("/bin/sh", None),
    ("/usr/bin/perl", None),
    ("/usr/bin/awk", None),
    ("/bin/csh", None),
    # Stuff that should always be substituted
    (".*bash$", "BASH_ADJ_FILES"),
    (".*python2", "PYTHON2_ADJ_FILES"),
    (".*python3", "PYTHON3_ADJ_FILES"),
    (".*python$", "PYTHON2_ADJ_FILES"),  # assume Python2
    (".*ruby$", "RUBY_ADJ_FILES"),
    (".*texlua$", "TEXLUA_ADJ_FILES"),
    (".*lua$", "LUA_ADJ_FILES"),  # must come after texlua XXX
    (".*wish8.5$", "WISH_ADJ_FILES"),
    (".*wish$", "WISH_ADJ_FILES"),
    (".*perl$", "MODPERL_ADJ_FILES"),
    (".*fontforge$", "FONTFORGE_ADJ_FILES"),
]
KNOWN_INTERPRETERS = OrderedDict((re.compile(pat), subst_var) for
                                 pat, subst_var in KNOWN_INTERPRETERS)


def match_interpreter(interp):
    for interp_re, subst_var in KNOWN_INTERPRETERS.iteritems():
        match = re.match(interp_re, interp)
        if match:
            return subst_var
    raise UnknownInterpreterError(interp)

def process_file(dirpath, filename, substs, strip_prefix):
    path = os.path.join(dirpath, filename)

    try:
        fh = open(path)
    except IOError:
        # ignore broken symlinks
        if os.path.islink(path):
            return
        raise

    line1 = fh.readline().strip()
    fh.close()

    # There are some `.in` files with placeholder shebangs, ignore.
    if "@" in line1 and filename.endswith(".in"):
        return

    # Search for a shebang and try to find the interpreter name
    match = re.match(ENV_SHEBANG_PATTERN, line1)
    if not match:
        match = re.match(SHEBANG_PATTERN, line1)
        if not match:
            return

    interp = match.group(1)
    subst_var = None
    try:
        subst_var = match_interpreter(interp)
    except UnknownInterpreterError as e:
        sys.stderr.write("warning: unknown interpreter: %s: %s\n" % (str(e), path))
        return

    if subst_var:
        substs[subst_var].add(os.path.relpath(path, strip_prefix))


def main(root_dir, strip_prefix):
    substs = defaultdict(set)
    for dirpath, dirname, filenames in os.walk(root_dir):
        for filename in filenames:
            process_file(dirpath, filename, substs, strip_prefix)

    print("# $OpenBSD$")
    print("#")
    print("# This file is automatically generated. Do not edit.\n")

    for subst_var, paths in sorted(substs.iteritems(), key=lambda t: t[0]):
        joined_paths = " \\\n\t".join(sorted(paths))
        print("\n%s += \\\n\t%s" % (subst_var, joined_paths))


if __name__ == "__main__":
    try:
        root_dir = sys.argv[1]
        strip_prefix = sys.argv[2]
    except IndexError:
        sys.stderr.write(__doc__)
        sys.exit(1)

    if not os.path.exists(root_dir):
        sys.stderr.write("mk_adj: root dir is non-existent\n")
        sys.exit(1)

    main(root_dir, strip_prefix)
