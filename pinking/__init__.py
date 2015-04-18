#!/usr/bin/env python

import curses
from importlib import import_module
import logging
import platform
from Queue import Queue
import subprocess
import sys
import threading


log = logging.getLogger()


def get_cpu_revision():
    for line in open('/proc/cpuinfo').readlines():
        if line.startswith('Revision'):
            return line[line.rfind(':') + 2:].strip()


class LogWindow(logging.Handler):
    def __init__(self, scr, level=logging.NOTSET):
        super(LogWindow, self).__init__(level)
        self.scr = scr
        self.entries = []

    def redraw(self):
        self.scr.clear()
        self.scr.border()
        h, w = self.scr.getmaxyx()

        num_entries = h - 2
        for line, record in enumerate(self.entries[-num_entries:]):
            # determine color
            if not curses.has_colors:
                color_pair = 0
            else:
                color_pair = curses.color_pair(7)

                if record.levelno >= logging.WARNING:
                    color_pair = curses.color_pair(3)
                if record.levelno >= logging.ERROR:
                    color_pair = curses.color_pair(1)

            entry = self.format(record)

            self.scr.addnstr(line+1, 1, entry, w-2, color_pair)
        self.scr.refresh()

    def handle(self, record):
        self.entries.append(record)
        self.dirty = True
