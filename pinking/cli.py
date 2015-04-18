from contextlib2 import ExitStack
import sys
import time

import click
import logbook

from .exc import LayoutNotFoundError
from .model import PinKingModel
from .ui import PinKingUI
from .util import curses_wrap, clock


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


def run_gpio_test(model, show_out):
    logbook.NullHandler(level=logbook.DEBUG).push_application()
    logbook.StderrHandler(level=logbook.INFO).push_application()

    poll_freq = 10.0
    click.echo('{} Hz'.format(poll_freq))

    def _on_iv_change(model, values):
        click.echo('IN: {}'.format(''.join('.' if v is None else str(v)
                                           for v in values)))

    def _on_ov_change(model, values):
        click.echo('OUT: {}'.format(''.join(map(str, values))))

    def _on_d_change(model, pin, direction):
        click.echo('#{} changed to {}'.format(
            pin + 1,
            'IN' if direction == model.gpio.IN else 'OUT',
        ))

    model.in_values_changed.connect(_on_iv_change)
    if show_out:
        model.out_values_changed.connect(_on_ov_change)
    model.direction_changed.connect(_on_d_change)

    # last 2 gpio pins are set to output
    out_pins = [p for p, n in enumerate(model.layout)
                if n.startswith('GPIO')][-2:]

    for pin in out_pins:
        model.set_direction(pin, model.gpio.OUT)
        model.set_output_value(pin, model.gpio.LOW)

    cycles = 0
    for missed_ticks in clock(1.0/poll_freq):
        cycles += 1 + missed_ticks

        if cycles > poll_freq:
            cycles = 0

            # every second ms, change an output pins
            out_pins[0], out_pins[1] = out_pins[1], out_pins[0]

            for n, pin in enumerate(out_pins):
                hl = model.gpio.HIGH if n % 2 else model.gpio.LOW
                model.set_direction(pin, model.gpio.OUT)
                model.set_output_value(pin, hl)

        model.read_input_values()
        if missed_ticks:
            click.echo('Missed clock ticks: {}'.format(missed_ticks))


@click.command()
@click.option('--fake-gpio', '-G', is_flag=True,
              help='Do not use GPIO library, fake input instead.')
@click.option('--rev', '-r',
              help='Manually specify hardware revision.')
@click.option('--test', '-t', is_flag=True,
              help='Run model test.')
@click.option('--test-show-out', is_flag=True,
              help='Show every output change when running output test.')
def main(fake_gpio, rev, test, test_show_out):
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
        click.echo('GPIO test mode.')
        run_gpio_test(model, test_show_out)
        sys.exit(0)

    with curses_wrap() as stdscr, ExitStack() as cleanup:
        cleanup.callback(gpio.cleanup)  # once we're done, reset GPIO pins

        ui = PinKingUI(stdscr, model)
        ui.run()
