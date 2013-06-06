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

import collections
import hashlib
import json
import os
import sys

from os.path import getsize, join

# if a list has > 1 entry then it's got dups.  so simple!  each key is as
# named, and each entry is a list of 'full paths', relative to the top root.
# partial_hash is performance improvement - read first block (512 bytes), and
# hash on that before reading whole, potentially large files.
by_name = {}
by_size = {}
by_partial_hash = {}
by_hash = {}

def update_by_name_and_by_size(path):
    for root, dirs, files in os.walk(path):
        sys.stdout.write(root + ' ')
        for name in files:
            full = join(root, name)
            try:
                size = getsize(full)
            except:
                continue    # XXX danger!
            name = name.lower()

            # update by_name
            bn = by_name.setdefault(name, full)
            if bn is not full:
                sys.stdout.write('n')
                if type(bn) is str:
                    by_name[name] = [bn, full]
                if type(bn) is list:
                    bn.append(full)

            # update by_size
            bs = by_size.setdefault(size, full)
            if bs is not full:
                sys.stdout.write('s')
                if type(bs) is str:
                    by_size[size] = [bs, full]
                    update_by_partial_hash(bs)  # chain -> by_partial_hash
                if type(bs) is list:
                    bs.append(full)
                update_by_partial_hash(full)    # chain -> by_partial_hash
        print
    print


def update_by_partial_hash(full):
    try:
        hash = hashlib.md5(open(full, 'rb').read(512)).hexdigest()
    except:
        return      # XXX danger!
    bph = by_partial_hash.setdefault(hash, full)
    if bph is not full:
        sys.stdout.write('H')
        if type(bph) is str:
            by_partial_hash[hash] = [bph, full]
            update_by_hash(bph)             # chain -> by_hash
        if type(bph) is list:
            bph.append(full)
        update_by_hash(full)                # chain -> by_hash


def update_by_hash(full):
    try:
        hash = hashlib.md5(open(full, 'rb').read()).hexdigest()
    except:
        return      # XXX danger!
    bh = by_hash.setdefault(hash, full)
    if bh is not full:
        sys.stdout.write('H')
        if type(bh) is str:
            by_hash[hash] = [bh, full]
        if type(bh) is list:
            bh.append(full)

# -----------------------------------------------------------------------------

update_by_name_and_by_size('.')

# save map as json to .duplicates.json
maps = { 'by_name': by_name, 'by_size': by_size, 'by_hash': by_hash }
json.dump(maps, open('.duplicates.json', 'wb'), indent=4)

# -----------------------------------------------------------------------------

print '\nby name:'
for name, fullnames in by_name.iteritems():
    if type(fullnames) is list:
        print '{0}: {1}'.format(name, ' '.join(fullnames))

print '\nby size:'
for size, fullnames in by_size.iteritems():
    if type(fullnames) is list:
        print '{0}: {1}'.format(size, ' '.join(fullnames))

print '\nby hash:'
for hash, fullnames in by_hash.iteritems():
    if type(fullnames) is list:
        print '{0}: {1}'.format(hash, ' '.join(fullnames))
