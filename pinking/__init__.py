#!/usr/bin/env python

import curses
import logging


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
