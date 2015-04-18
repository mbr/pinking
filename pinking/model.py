import curses

from logbook import Logger

from .exc import LayoutNotFoundError


PIN_LAYOUT = {
    # http://www.element14.com/community/docs/DOC-73950
    # /l/raspberry-pi-2-model-b-gpio-40-pin-block-pinout

    # Raspberry Pi 2:
    'a01041': [
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

# China RasPi 2 == UK Raspi 2
PIN_LAYOUT['a21041'] = PIN_LAYOUT['a01041']


log = Logger('model')


class Observable(object):
    def __init__(self):
        self.observers = []

    def register_observer(self, callback):
        self.observers.append(callback)

    def notify(self):
        for obs in self.observers:
            obs()


class PinKingModel(Observable):
    RESERVED_PINS = ('GND', '5V', '3V3', 'ID_SC', 'ID_SD')

    def __init__(self, gpio, rev):
        super(PinKingModel, self).__init__()
        self.rev = rev
        try:
            self.layout = PIN_LAYOUT[rev]
        except KeyError as e:
            raise LayoutNotFoundError(e)

        self.selected_pin = 0
        self.directions = [None] * len(layout)
        self.out_values = [0] * len(layout)
        self.in_values = [0] * len(layout)
        self.gpio = gpio

        # set GPIO mode
        self.gpio.setmode(self.gpio.BOARD)

        self.reset_channels()

    def _on_edge_detect(self, channel):
        GPIO = self.gpio

        pin = channel - 1
        log.debug('Edge detected on {}'.format(channel))

        nv = GPIO.input(channel)
        if nv != self.in_values[pin]:
            self.in_values[pin] = nv
            self.notify()

    def set_direction(self, pin, d):
        GPIO = self.gpio

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
        self.gpio.output(channel, value)

        self.notify()

    def read_input_values(self):
        GPIO = self.gpio
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
            self.set_direction(n, self.gpio.IN)

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

