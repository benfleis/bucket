#!/usr/bin/env python

##
# quick and dirty duplicate file detection.
#
# strategy: walk files.  record name and file size.  if another file with
# identical file size is found, do md5 on both.  report all identically named,
# and identically hashed files.  done.
#
# follow up: for big performance improvement, do 2 layers of hash checks; first
# just by first 512 bytes of file, then by whole file
#
#
# FUTURE:
#   - add cmd line opts, most notably starting dir and exclude opts
#   - add option to toggle shell escaping of outputs
#   - add option to turn on/off name/size/hash outputs
#   - add option to load/use cache
#

import argparse
import collections
import fnmatch
import hashlib
import json
import os
import pipes    # for pipes.quote, shell escaping: http://stackoverflow.com/questions/35817/how-to-escape-os-system-calls-in-python
import re
import sys

from os.path import getsize, join, splitext

# each key is as named, and each entry is a string or a set of 'full paths',
# relative to the top root.  partial_hash is performance improvement - read
# first block (512 bytes), and hash on that before reading whole, potentially
# large files.

by_ext = collections.defaultdict(lambda:
    { 'by_name': {}, 'by_size': {}, 'by_partial_hash': {}, 'by_hash': {}, },)

def update_by_name_and_by_size(path, exclude=None, include=None, delete=False):
    for root, dirs, files in os.walk(unicode(path)):
        if exclude:
            # filter excluded dirs
            to_del = []
            for i, d in enumerate(dirs):
                if exclude.match(join(root, d)):
                    to_del.append(i)
            for i in reversed(to_del):
                del dirs[i]

        if exclude:
            # filter non-included dirs
            to_del = []
            for i, d in enumerate(dirs):
                if not include.match(join(root, d)):
                    to_del.append(i)
            for i in reversed(to_del):
                del dirs[i]

        sys.stdout.write(root + u' ')
        for name in files:
            # skip if excluded file, then get name/size/ext
            full = join(root, name)
            if exclude and exclude.match(full):
                continue
            if include and not include.match(full):
                continue
            try: size = getsize(full)
            except: continue
            name = name.lower()
            bev = by_ext[os.path.splitext(name)[1]]

            # update by_name
            bnv = bev['by_name'].setdefault(name, full)
            if bnv is not full:
                if type(bnv) is unicode:
                    bev['by_name'][name] = set((bnv, full))
                if type(bnv) is set:
                    bnv.add(full)

            # update bev['by_size']
            bsv = bev['by_size'].setdefault(size, full)
            if bsv is not full:
                if type(bsv) is unicode:
                    bev['by_size'][size] = set((bsv, full))
                    update_by_partial_hash(bev, bsv, delete)
                if type(bsv) is set:
                    bsv.add(full)
                update_by_partial_hash(bev, full, delete)
        print


def update_by_partial_hash(bev, full, delete):
    try: hash = hashlib.md5(open(full, 'rb').read(512)).hexdigest()
    except: return
    bphv = bev['by_partial_hash'].setdefault(hash, full)
    if bphv is not full:
        if type(bphv) is unicode:
            bev['by_partial_hash'][hash] = set((bphv, full))
            update_by_hash(bev, bphv, delete)
        if type(bphv) is set:
            bphv.add(full)
        update_by_hash(bev, full, delete)


def update_by_hash(bev, full, delete):
    try: input = open(full, 'rb', 64 * 1024)
    except: return
    md5 = hashlib.md5()
    map(md5.update, input)
    hash = md5.hexdigest()

    bhv = bev['by_hash'].setdefault(hash, full)
    if bhv is not full:
        if type(bhv) is unicode:
            bev['by_hash'][hash] = [bhv, full]
            if delete:
                delete.append(full, bhv)
        if type(bhv) is list:
            bhv.append(full)
            if delete:
                delete.append(bhv[-1], bhv[0])

# -----------------------------------------------------------------------------

def main(args):
    # quick arg parsing
    p = argparse.ArgumentParser(description='look for duplicate files')
    p.add_argument('--exclude', action='append', help='exclude glob pattern')
    p.add_argument('--include', action='append', help='include glob pattern')
    p.add_argument('--delete-script', dest='delete_script', help=''.join([
        'Generate shell script to delete all duplicates found in 2nd, 3rd, ',
        'etc., specified paths, placed in named file.  Must specify more ',
        'than one path.']))
    p.add_argument('paths', nargs='+', help='paths to search')
    args = p.parse_args(args[1:])
    if (args.delete_script and len(args.paths) < 2):
        p.print_help(sys.stderr)
        return 1
    if len(args.paths) != len(set(args.paths)):
        sys.stderr.write('Redundant PATHS found: {0}\n\n'.format(args.paths))
        p.print_usage(sys.stderr)
        return 1

    # convert set of globs into a singular RE
    exclude = None if not args.exclude else re.compile('(?:{0})'.format(
        ')|(?:'.join([fnmatch.translate(ex) for ex in args.exclude])))
    include = None if not args.include else re.compile('(?:{0})'.format(
        ')|(?:'.join([fnmatch.translate(ex) for ex in args.include])))
    delete = None if not args.delete_script else DeleteScriptGenerator()

    update_by_name_and_by_size(args.paths[0], exclude, include, None)
    for path in args.paths[1:]:
        update_by_name_and_by_size(path, exclude, include, delete)

    if delete:
        delete.write(args.delete_script)

    # save raw map as json to .duplicates.json
    class JsonSetEncoder(json.JSONEncoder):
        def default(self, obj):
            if type(obj) is set:
                return list(obj)
    json.dump(by_ext, open('.duplicates.json', 'wb'), indent=4, cls=JsonSetEncoder)

    # -------------------------------------------------------------------------

    already = set()

    print '\nby hash:'
    for ext, maps in by_ext.iteritems():
        for hash, fullnames in maps['by_hash'].iteritems():
            if type(fullnames) is list:
                print u'{0}: {1}'.format(hash, u' '.join(map(pipes.quote, fullnames)))
                already.update(fullnames)

    print '\nby name:'
    for ext, maps in by_ext.iteritems():
        for name, fullnames in maps['by_name'].iteritems():
            if type(fullnames) is set:
                notyet = fullnames.difference(already)
                if notyet:
                    print u'{0}: {1}'.format(name, u' '.join(map(pipes.quote, notyet)))
                    already.update(notyet)


# -----------------------------------------------------------------------------

class DeleteScriptGenerator:
    def __init__(self):
        self.header = '#!/bin/sh\n\n'
        self.lines = []
        self.line_max = 0

    def append(self, full, duplicate_of=None):
        line = 'rm {0}'.format(pipes.quote(full))
        self.lines.append((line, duplicate_of))
        self.line_max = max(self.line_max, len(line))

    def write(self, filename):
        if not self.lines:
            return

        out = open(filename, 'w')
        off = ((self.line_max + 4) / 4) * 4
        fmt = '{0:' + str(off) + 's}# {1}\n'
        for line, duplicate_of in self.lines:
            if duplicate_of:
                out.write(fmt.format(line, duplicate_of))
            else:
                out.write('{0}\n'.format(line))
        out.close()

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    sys.exit(main(sys.argv))
