import curses
import sys

import click

from .lib import PIN_LAYOUT, PKG_NAMES


HOME_URL = 'https://github.com/mbr/pinking'


@click.command()
@click.option('--fake-gpio', '-G', is_flag=True,
              help='Do not use GPIO library, fake input instead.')
@click.option('--rev', '-r',
              help='Manually specify hardware revision.')
def main(fake_gpio, rev):
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

    if rev is None:
        rev = GPIO.RPI_INFO['REVISION']

    click.echo('Using GPIO: {}'.format(GPIO))
    click.echo('Model [{}]: {[TYPE]}'.format(rev, GPIO.RPI_INFO))

    if not rev in PIN_LAYOUT:
        click.echo('I don\'t know the pin layout for {}. Sorry.\n'
                   'Please report this issue to {}'
                   .format(rev, HOME_URL))
        sys.exit(1)

    # FIXME: somehow, restore \n -> \r\n after curses exists
    try:
        curses.wrapper(run_gui, pi_rev)
    finally:
        GPIO.cleanup()
