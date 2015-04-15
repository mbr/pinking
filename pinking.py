#!/usr/bin/env python

from importlib import import_module
import os
import platform
import subprocess
import sys


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


def try_imports(*names):
    mods = []
    missing = []

    for name in names:
        try:
            mods.append(import_module(name))
        except ImportError:
            missing.append(name)

    if missing:
        msg(
            'The following packages could not be imported: {}'.
            format(', '.join(missing))
        )

        # if not platform.dist()[0] == 'debian':
        #     exiterror('Please install the missing packages.')

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
        return try_imports(*names)

    return mods


def ensure_uid_0():
    if os.getuid() != 0:
        exiterror('pinking requires root permissions to access GPIO pins. '
                  'Try\n'
                  '  sudo {}'.format(sys.argv[0]))


def main():
    ensure_uid_0()

    GPIO = try_imports('RPi.GPIO')
    print GPIO


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


if __name__ == '__main__':
    main()
