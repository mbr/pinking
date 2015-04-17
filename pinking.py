#!/usr/bin/env python

import curses
from importlib import import_module
import logging
import os
import platform
from Queue import Queue
import subprocess
import sys
import threading

import click


log = logging.getLogger()

HOME_URL = 'https://github.com/mbr/pinking'


# the "Fake GPIO" module
class FakeGPIO(object):
    BOARD = None
    IN = -1
    OUT = 1
    LOW = 0
    HIGH = 1

    def __getattr__(self, name):
        def f(*args):
            log.debug('FakeGPIO: {}({})'.format(name, ', '.join(
                map(str, args)))
            )
        return f


# contains a suggestion for installation for various potentially missing
# module
PKG_NAMES = {
    2: {
        'RPi.GPIO': 'python-rpi.gpio',
    },
    3: {
        'RPi.GPIO': 'python3-rpi.gpio',
    }
}


PI_MODELS = {
    # from http://www.raspberrypi-spy.co.uk/2012/09/
    #      checking-your-raspberry-pi-board-version/
    '0002': 'RPi1_B_1.0_256',
    '0003': 'RPi1_B_1.0_ECN0001_256',
    '0004': 'RPi1_B_2.0_256',
    '0005': 'RPi1_B_2.0_256',
    '0006': 'RPi1_B_2.0_256',
    '0007': 'RPi1_A_256',
    '0008': 'RPi1_A_256',
    '0009': 'RPi1_A_256',
    '000d': 'RPi1_B_2.0_512',
    '000e': 'RPi1_B_2.0_512',
    '000f': 'RPi1_B_2.0_512',
    '0010': 'RPi1_B+_512',
    '0011': 'RPi1_Compute_Module_512',
    '0012': 'RPi1_A+_256',
    'a01041': 'Rpi2_B_UK_1024',
    'a21041': 'Rpi2_B_China_1024',
}


def get_cpu_revision():
    for line in open('/proc/cpuinfo').readlines():
        if line.startswith('Revision'):
            return line[line.rfind(':') + 2:].strip()


PIN_LAYOUT = {
    # http://www.element14.com/community/docs/DOC-73950
    # /l/raspberry-pi-2-model-b-gpio-40-pin-block-pinout
    'Rpi2_B_UK_1024': [
        # 1            2
        '3V3',         '5V',
        'GPIO02',      '5V',
        'GPIO03',      'GND',
        'GPIO04',      'GPIO14',
        'GND',         'GPIO15',
        # 11           12
        'GPIO17',      'GPIO18',
        'GPIO27',      'GND',
        'GPIO22',      'GPIO23',
        '3V3',         'GPIO24',
        'GPIO10',      'GND',
        # 21           22
        'GPIO09',      'GPIO25',
        'GPIO11',      'GPIO08',
        'GND',         'GPIO07',
        'ID_SD',       'ID_SC',
        'GPIO05',      'GND',
        # 31           32
        'GPIO06',      'GPIO12',
        'GPIO13',      'GND',
        'GPIO19',      'GPIO16',
        'GPIO26',      'GPIO20',
        'GND',         'GPIO21',
    ]
}

# aliases:
PIN_LAYOUT['Rpi2_B_China_1024'] = PIN_LAYOUT['Rpi2_B_UK_1024']


def exiterror(message, status=1):
    msg(message)
    sys.exit(status)


def msg(message):
    sys.stderr.write(message)
    sys.stderr.write('\n')


def confirm(message, default=True):
    def prompt():
        sys.stderr.write(message)
        sys.stderr.write(' [Y/n]: ' if default else ' [y/N]: ')
        v = raw_input().lower()

        if v == 'y':
            return True

        if v == 'n':
            return False

        if v == '':
            return default

    inp = None
    while inp is None:
        inp = prompt()

    return inp


def try_imports(names):
    mods = {}
    missing = []

    for name, modname in names.items():
        try:
            mods[name] = import_module(modname)
        except ImportError:
            missing.append(name)

    if missing:
        msg(
            'The following packages could not be imported: {}'.
            format(', '.join(missing))
        )

        if not platform.dist()[0] == 'debian':
            exiterror('Please install the missing packages.')

        # we're hopefully on raspbian
        debs = []
        pkg_names = PKG_NAMES[sys.version_info.major]
        for name in missing:
            if not name in pkg_names:
                exiterror('I cannot automatically install {}, please install '
                          'the missing pacakges.'.format(name))
            debs.append(pkg_names[name])

        cmd = ['apt-get', 'install', '-y'] + debs

        msg(
            'These can be installed by running\n'
            '  sudo {}'.format(' '.join(cmd))
        )
        if confirm('Do you want me to run this command for you now?'):
            if subprocess.call(cmd) != 0:
                exiterror('Installation failed.')
        else:
            exiterror('Cannot continue with missing packages.')

        # auto-installation succeeded (hopefully)
        return try_imports(names)

    return mods


def ensure_uid_0():
    if os.getuid() != 0:
        exiterror('pinking requires root permissions to access GPIO pins. '
                  'Try\n'
                  '  sudo {}'.format(sys.argv[0]))


@click.command()
@click.option('--fake-gpio', '-G', is_flag=True,
              help='Do not use GPIO library, fake input instead.')
@click.option('--rev', '-r', type=click.Choice(PI_MODELS.values()),
              help='Manually specify hardware revision.')
def main(fake_gpio, rev):
    ensure_uid_0()

    required_modules = {
    }

    if not fake_gpio:
        required_modules['GPIO'] = 'RPi.GPIO'
    else:
        globals()['GPIO'] = FakeGPIO()

    # import the modules we need
    globals().update(try_imports(required_modules))

    if not rev:
        pi_rev = PI_MODELS.get(get_cpu_revision(), None)
        if not pi_rev:
            exiterror('Found the following Revision in /proc/cpuinfo, which '
                      'is not one I recognize: {}\n'
                      'You can manually specify one of\n  {}\n\nusing the '
                      '--rev command line option'
                      .format(pi_rev, '\n  '.join(
                          sorted(PI_MODELS.values()))
                      ))
    else:
        pi_rev = rev

    if not pi_rev in PIN_LAYOUT:
        exiterror('I don\'t know the pin layout for {}. Sorry.\n'
                  'Please report this issue to {}'
                  .format(pi_rev, HOME_URL))

    # FIXME: somehow, restore \n -> \r\n after curses exists
    try:
        curses.wrapper(run_gui, pi_rev)
    finally:
        GPIO.cleanup()


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


if __name__ == '__main__':
    main()
