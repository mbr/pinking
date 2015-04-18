from contextlib2 import ExitStack
import sys

import click

from .exc import LayoutNotFoundError
from .model import PinKingModel
from .ui import PinKingUI
from .util import curses_wrap


HOME_URL = 'https://github.com/mbr/pinking'

if sys.version_info.major == 2:
    PKG_NAMES = {
        'RPi.GPIO': 'python-rpi.gpio',
    }
elif sys.version_info.major == 3:
    PKG_NAMES = {
        'RPi.GPIO': 'python3-rpi.gpio',
    }
else:
    PKG_NAMES = {}


def load_gpio(fake_gpio):
    if fake_gpio:
        from .fakegpio import GPIO
    else:
        try:
            from RPi import GPIO
        except ImportError:
            click.echo('The RPi.GPIO module could not be imported. Please '
                       'install by running\n\n    $ ' +
                       click.style('sudo apt-get install {}'
                                   .format(PKG_NAMES['RPi.GPIO']), bold=True)
                       + '\n')
            click.echo('Alternatively, you can use the fake GPIO module '
                       'by passing --fake-gpio. This will *not* cause any '
                       'actual hardware pins to be read!')
            sys.exit(1)

    return GPIO


@click.command()
@click.option('--fake-gpio', '-G', is_flag=True,
              help='Do not use GPIO library, fake input instead.')
@click.option('--rev', '-r',
              help='Manually specify hardware revision.')
@click.option('--test', '-t', is_flag=True,
              help='Run model test.')
def main(fake_gpio, rev, test):
    gpio = load_gpio(fake_gpio)

    if rev is None:
        rev = gpio.RPI_INFO['REVISION']

    click.echo('Using GPIO: {}'.format(gpio))
    click.echo('Model [{}]: {[TYPE]}'.format(rev, gpio.RPI_INFO))

    try:
        # instantiate model
        model = PinKingModel(gpio, rev)
    except LayoutNotFoundError as e:
        click.echo('No pin layout known for {}.\n'
                   'Please report this issue to {}'.format(e, HOME_URL))
        sys.exit(1)

    if test:
        click.echo('Running model test.')
        pass
        sys.exit(0)

    with curses_wrap() as stdscr, ExitStack() as cleanup:
        cleanup.callback(gpio.cleanup)  # once we're done, reset GPIO pins

        ui = PinKingUI(stdscr, model)
        ui.run()
