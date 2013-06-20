#!/usr/bin/env python

##
# rename files like '*.JPG' -> '*.jpg'
# zmv can do this just fine, if not on an annoying file system like Mac's
# case-insensitive variant, which still records original case, and respects
# case with utils like .JPG.  SIGH.
#
# so we have to do a non-atomic double rename here.  double sigh.
#
# basic mode: read stdin, separating on white-space (or on '\0' if -0 opt
# given, for find -print0 compatibility win).  each thing that comes along gets
# file extesion split, and BAM!  renamed.
#

import argparse
import os
import sys


# -----------------------------------------------------------------------------

def main(args):
    # quick arg parsing
    p = argparse.ArgumentParser(description='look for duplicate files')
    p.add_argument('-0', dest='nul_separator', action='store_true', help='use NUL (\'\\0\') char as separator, a la xargs')
    p.add_argument('-n', '--dry-run', dest='dry_run', action='store_true', help='dry run: do not perform actual moves')
    p.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='verbose mode')
    args = p.parse_args(args[1:])

    def rename(src):
        bits = os.path.splitext(src)
        dst = bits[0] + bits[1].lower()
        if src != dst:
            tmp = bits[0] + '-LOWER_CASE_HOLDER' + bits[1].lower()
            if args.verbose:
                print '{0} -> {1}'.format(src, tmp)
            if not args.dry_run:
                os.rename(src, tmp)
            if args.verbose:
                print '{0} -> {1}'.format(tmp, dst)
            if not args.dry_run:
                os.rename(tmp, dst)

    if args.nul_separator:
        buf = ''
        while True:
            c = sys.stdin.read(1)
            if c == '':
                if buf:
                    rename(buf)
                break
            elif c == '\0':
                if buf:
                    rename(buf)
                    buf = ''
                continue
            else:
                buf += c
    else:
        for line in sys.stdin:
            for f in line.split():
                rename(f)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
