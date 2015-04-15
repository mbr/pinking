#!/usr/bin/env python

import argparse
import curses
from importlib import import_module
import os
import platform
import subprocess
import sys


HOME_URL = 'https://github.com/mbr/pinking'


# the "Fake GPIO" module
class FakeGPIO(object):
    pass


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
            return line[line.rfind(':'):].strip()


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fake-gpio', action='store_true',
                        help='Do not use GPIO library, fake input instead.')
    parser.add_argument('--rev', choices=PI_MODELS.values(),
                        help='Manually specify hardware revision.')
    args = parser.parse_args()

    ensure_uid_0()

    required_modules = {
    }

    if not args.fake_gpio:
        required_modules['GPIO'] = 'RPi.GPIO'
    else:
        globals()['GPIO'] = FakeGPIO

    # import the modules we need
    globals().update(try_imports(required_modules))

    if not args.rev:
        pi_rev = get_cpu_revision()

        if not pi_rev in PI_MODELS:
            exiterror('Found the following Revision in /proc/cpuinfo, which '
                      'is not one I recognize: {}\n'
                      'You can manually specify one of\n  {}\n\nusing the '
                      '--rev command line option'
                      .format(pi_rev, '\n  '.join(
                          sorted(PI_MODELS.values()))
                      ))
    else:
        pi_rev = args.rev

    if not pi_rev in PIN_LAYOUT:
        exiterror('I don''t know the pin layout for {}. Sorry.\n'
                  'Please report this issue to {}'
                  .format(pi_rev, HOME_URL))

    # FIXME: somehow, restore \n -> \r\n after curses exists
    curses.wrapper(run_gui, pi_rev)


def run_gui(scr, pi_rev):
    # turn off cursor
    curses.curs_set(0)
    pwin = scr

    layout = PIN_LAYOUT[pi_rev]

    # the pin-layout window
    label_width = max(len(n) for n in layout)

    # label format left and right
    lfmt = ('{:>%d}' % label_width,
            '{:<%d}' % label_width)
    pfmt = '{:2}'

    for pin, name in enumerate(layout):
        row = pin // 2
        col = pin % 2

        # row:
        #   lw
        # **lw** XX XX **lw**

        label = lfmt[col].format(layout[pin])
        pwin.addstr(row, col * (label_width + 7), label)

        # draw pin:
        num = pfmt.format(pin)
        pwin.addstr(row, label_width + 1 + col * 3, num)

    pwin.refresh()

    # busy work for now
    while True:
        pass


if __name__ == '__main__':
    main()
