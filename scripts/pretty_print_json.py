#!/usr/bin/env python

import json, sys

input = open(sys.argv[1], 'rb') if len(sys.argv) >= 2 else sys.stdin
output = open(sys.argv[2], 'wb') if len(sys.argv) >= 3 else sys.stdout
json.dump(json.load(input), output, indent=4)
