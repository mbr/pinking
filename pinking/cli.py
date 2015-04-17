import sys

import click

from .lib import PI_MODELS, PKG_NAMES


@click.command()
@click.option('--fake-gpio', '-G', is_flag=True,
              help='Do not use GPIO library, fake input instead.')
@click.option('--rev', '-r', type=click.Choice(PI_MODELS.values()),
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

    click.echo('Using GPIO: {}'.format(GPIO))
