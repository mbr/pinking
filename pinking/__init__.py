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


class PinModel(Observable):
    RESERVED_PINS = ('GND', '5V', '3V3', 'ID_SC', 'ID_SD')

    def __init__(self, layout):
        super(PinModel, self).__init__()
        self.layout = layout
        self.selected_pin = 0
        self.directions = [None] * len(layout)
        self.out_values = [0] * len(layout)
        self.in_values = [0] * len(layout)

        # set GPIO mode
        GPIO.setmode(GPIO.BOARD)

    def _on_edge_detect(self, channel):
        pin = channel - 1
        log.debug('Edge detected on {}'.format(channel))

        nv = GPIO.input(channel)
        if nv != self.in_values[pin]:
            self.in_values[pin] = nv
            self.notify()

    def set_direction(self, pin, d):
        channel = pin + 1

        name = self.layout[pin]

        if name in self.RESERVED_PINS:
            self.directions[pin] = None
            return  # ignore ground
        self.directions[pin] = d

        GPIO.setup(channel, d, pull_up_down=GPIO.PUD_DOWN)

        if d == GPIO.IN:
            GPIO.add_event_detect(channel, GPIO.BOTH, self._on_edge_detect)
        else:
            # remove previously installed event handler
            GPIO.remove_event_detect(channel)

        log.debug('Setting pin direction: {} #{} {}'.format(
            'in' if d == GPIO.IN else 'out', pin, self.layout[pin],
        ))

    def set_output_value(self, pin, value):
        self.out_values[pin] = value

        log.debug('Setting output: {} #{} {}'.format(
            value, pin, self.layout[pin],
        ))
        GPIO.output(channel, value)

        self.notify()

    def read_input_values(self):
        changed = False

        for pin, d in enumerate(self.directions):
            if d == GPIO.IN:
                nv = GPIO.input(pin + 1)
                if nv != self.in_values[pin]:
                    self.in_values[pin] = nv
                    changed = True

        if changed:
            self.notify()

    def reset_channels(self):
        for n, name in enumerate(self.layout):
            self.set_direction(n, GPIO.IN)

        self.read_input_values()

    def handle_keypress(self, keycode):
        # controller code, tacked onto model. sorry
        if keycode == ord('j') or keycode == curses.KEY_DOWN:
            self.selected_pin += 2
            self.selected_pin %= len(self.layout)
            self.notify()
            return True
        if keycode == ord('k') or keycode == curses.KEY_UP:
            self.selected_pin -= 2
            self.selected_pin %= len(self.layout)
            self.notify()
            return True
        if keycode == ord('h') or keycode == curses.KEY_LEFT:
            if self.selected_pin % 2:
                self.selected_pin -= 1
                self.selected_pin %= len(self.layout)
                self.notify()
            return True
        if keycode == ord(';') or keycode == curses.KEY_RIGHT:
            if not self.selected_pin % 2:
                self.selected_pin += 1
                self.selected_pin %= len(self.layout)
                self.notify()
            return True
        if keycode == ord('d'):
            old_dir = self.directions[self.selected_pin]
            if old_dir is not None:
                self.set_direction(
                    self.selected_pin,
                    GPIO.IN if old_dir == GPIO.OUT else GPIO.OUT
                )
                self.notify()
            else:
                curses.flash()
            return True
        if keycode == ord('t') or keycode == ord('\n'):
            if self.directions[self.selected_pin] == GPIO.OUT:
                self.set_output_value(
                    self.selected_pin,
                    GPIO.LOW if self.out_values[self.selected_pin] ==
                    GPIO.HIGH else GPIO.HIGH
                )
            return True
        if keycode == ord('r'):
            self.read_input_values()
            log.info(''.join(map(str, self.in_values)))
            return True


class GuiController(object):
    def handle_keypress(self, keycode):
        if keycode == ord('q'):
            sys.exit(0)
            return True


def read_keypresses(scr, q):
    while True:
        ch = scr.getch()

        if ch is not -1:
            q.put(('keypress', ch))


def run_gui(scr, pi_rev):
    events = Queue()

    # start listening to keyboard events
    key_thread = threading.Thread(target=read_keypresses, args=(scr, events))
    key_thread.daemon = True
    key_thread.start()

    # turn off cursor
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_BLUE, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)

    layout = PIN_LAYOUT[pi_rev]

    ctrl = GuiController()
    pm = PinModel(layout)
    pm.reset_channels()

    pw = PinWindow.from_model(pm)

    ctrls = [
        ctrl,
        pm,
    ]

    screen_height, screen_width = scr.getmaxyx()

    # add logging window
    lwin = LogWindow(curses.newwin(screen_height - pw.height - 1,
                                   screen_width,
                                   pw.height + 1,
                                   0))

    log.setLevel(logging.DEBUG)
    log.addHandler(lwin)

    log.debug('Starting event loop...')

    while True:
        if lwin.dirty:
            lwin.redraw()

        ev = events.get()

        if 'keypress' == ev[0]:
            keycode = ev[1]
            # let any controller handle the keypress
            for c in ctrls:
                if c.handle_keypress(keycode):
                    continue
        else:
            raise RuntimeError('Received unexpected event {}'
                               .format(ev))
