#!/usr/bin/env python

# eye candy!
class Spinner(object):
    #outs = ['[  ', ' ~ ', '  ]', ' _ ']
    #outs = ['|O|', '/o\\', '-.-', '\\_/',]
    outs = ['\\', '|', '/', '-']

    def __init__(self, out=sys.stderr, header='', footer='', dots=None):
        self.header = header
        self.footer = footer

        self.state = 'init'
        self.count = -1
        self.out = out
        self.dots = dots

    def __del__(self):
        done()

    def next(self, text=None):
        if self.state == 'init':
            self.out.write(self.header)
            self.state = 'next'
        else:
            self.out.write('\x08' * len(self.outs[(self.count)]))

        if text is not None:
            self.out.write(text)

        self.count = (self.count + 1) % len(self.outs)
        self.out.write(self.outs[self.count])
        self.out.flush()

        if self.dots is not None \
           and self.count % self.dots == self.dots - 1:
            self.out.write('\x08. ')
            self.out.flush()

    def done(self):
        if self.state == 'next':    # do nothing if init -> done
            self.out.write('\x08' * len(self.outs[(self.count)]) + self.footer)
        self.state = 'done'
