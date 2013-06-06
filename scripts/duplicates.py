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

import collections
import hashlib
import json
import os
import pipes    # for pipes.quote, shell escaping: http://stackoverflow.com/questions/35817/how-to-escape-os-system-calls-in-python
import sys

from os.path import getsize, join

# each key is as named, and each entry is a string or a set of 'full paths',
# relative to the top root.  partial_hash is performance improvement - read
# first block (512 bytes), and hash on that before reading whole, potentially
# large files.
by_name = {}
by_size = {}
by_partial_hash = {}
by_hash = {}


def update_by_name_and_by_size(path):
    for root, dirs, files in os.walk(unicode(path)):
        sys.stdout.write(root + u' ')
        out = ''
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
                out = 'n'
                if type(bn) is unicode:
                    by_name[name] = set((bn, full))
                if type(bn) is set:
                    bn.add(full)

            # update by_size
            bs = by_size.setdefault(size, full)
            if bs is not full:
                if size > 0:
                    out += 's'
                if type(bs) is unicode:
                    by_size[size] = set((bs, full))
                    if size > 0:
                        update_by_partial_hash(bs)
                if type(bs) is set:
                    bs.add(full)
                if size > 0:
                    out = update_by_partial_hash(full, out)

            if out:
                sys.stdout.write(out)
        print
    print


def update_by_partial_hash(full, out=''):
    try:
        hash = hashlib.md5(open(full, 'rb').read(512)).hexdigest()
    except:
        return      # XXX danger!
    bph = by_partial_hash.setdefault(hash, full)
    if bph is not full:
        if type(bph) is unicode:
            by_partial_hash[hash] = set((bph, full))
            update_by_hash(bph)
        if type(bph) is set:
            bph.add(full)
        out = update_by_hash(full, out)
    return out


def update_by_hash(full, out=''):
    try:
        hash = hashlib.md5(open(full, 'rb').read()).hexdigest()
    except:
        return      # XXX danger!
    bh = by_hash.setdefault(hash, full)
    if bh is not full:
        if type(bh) is unicode:
            by_hash[hash] = set((bh, full))
        if type(bh) is set:
            bh.add(full)
        out = out[0:-1] + 'H'
    return out


# -----------------------------------------------------------------------------

update_by_name_and_by_size('.')

# save raw map as json to .duplicates.json
maps = { 'by_name': by_name, 'by_size': by_size, 'by_hash': by_hash }
class JsonSetEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is set:
            return list(obj)
json.dump(maps, open('.duplicates.json', 'wb'), indent=4, cls=JsonSetEncoder)

# -----------------------------------------------------------------------------

already = set()

print '\nby hash:'
for hash, fullnames in by_hash.iteritems():
    if type(fullnames) is set:
        print u'{0}: {1}'.format(hash, u' '.join(map(pipes.quote, fullnames)))
        already.update(fullnames)

#print '\nby size:'
#for size, fullnames in by_size.iteritems():
#    if type(fullnames) is set:
#        notyet = fullnames.difference(already)
#        if notyet:
#            print u'{0}: {1}'.format(size, u' '.join(map(pipes.quote, notyet)))
#            already.update(notyet)

print '\nby name:'
for name, fullnames in by_name.iteritems():
    if type(fullnames) is set:
        notyet = fullnames.difference(already)
        if notyet:
            print u'{0}: {1}'.format(name, u' '.join(map(pipes.quote, notyet)))
            already.update(notyet)

