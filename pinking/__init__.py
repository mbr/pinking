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


# the "Fake GPIO" module
class FakeGPIO(object):
    BOARD = None
    IN = -1
    OUT = 1
    LOW = 0
    HIGH = 1


def get_cpu_revision():
    for line in open('/proc/cpuinfo').readlines():
        if line.startswith('Revision'):
            return line[line.rfind(':') + 2:].strip()


class Observable(object):
    def __init__(self):
        self.observers = []

    def register_observer(self, callback):
        self.observers.append(callback)

    def notify(self):
        for obs in self.observers:
            obs()


class Widget(object):
    @property
    def height(self):
        return self.scr.getmaxyx()[0]

    @property
    def width(self):
        return self.scr.getmaxyx()[1]


class PinWindow(Widget):
    def __init__(self, scr, model):
        self.scr = scr
        self.model = model
        model.register_observer(self.redraw)
        self.redraw()

    def redraw(self):
        layout = self.model.layout
        selected = self.model.selected_pin
        scr = self.scr
        scr.clear()

        # calculate the maximum width required for any label
        label_width = max(len(n) for n in layout)

        # label format left and right
        lfmt = ('{:>%d}' % label_width,
                '{:<%d}' % label_width)
        pfmt = '[{:2}]'

        for pin, name in enumerate(layout):
            row = pin // 2
            col = pin % 2

            color = curses.color_pair(0)
            extra_label = color
            extra_pin = color

            if pin == selected:
                extra_label = curses.A_BOLD
                extra_pin = curses.A_BOLD

            # direction
            pdir = self.model.directions[pin]
            value = None

            if pdir == GPIO.IN:
                color = curses.color_pair(6)
                value = self.model.in_values[pin]
            elif pdir == GPIO.OUT:
                color = curses.color_pair(2)
                value = self.model.out_values[pin]

            # output or input value
            if value == GPIO.HIGH:
                extra_label |= curses.A_REVERSE
                extra_pin |= curses.A_REVERSE

            # special names
            if name in ('5V', '3V3'):
                color = curses.color_pair(1)
            elif name == 'GND':
                color = curses.color_pair(3)

            # add colors
            extra_label |= color

            label = lfmt[col].format(layout[pin])
            scr.addstr(row, col * (label_width + 11), label, extra_label)

            # draw pin:
            num = pfmt.format(pin + 1)
            scr.addstr(row, label_width + 1 + col * 5, num, extra_pin)

        scr.refresh()

    @classmethod
    def from_model(cls, model, y=0, x=0):
        label_width = max(len(n) for n in model.layout)

        w = 2 * label_width + 12
        mlen = len(model.layout)
        h = mlen // 2

        scr = curses.newwin(h, w, y, x)

        return cls(scr, model)


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
