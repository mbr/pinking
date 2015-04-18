import curses

from blinker import Signal
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
RESERVED_PINS = ('GND', '5V', '3V3', 'ID_SC', 'ID_SD')


# China RasPi 2 == UK Raspi 2
PIN_LAYOUT['a21041'] = PIN_LAYOUT['a01041']


log = Logger('model')


class PinKingModel(object):
    # signals
    pin_selected = Signal(doc='The currently selected ``pin`` changed.')
    direction_changed = Signal(doc='``pin`` changed its input/output '
                                   'direction to ``direction``')
    in_values_changed = Signal(doc='``values`` changed')
    out_values_changed = Signal(doc='``values`` changed')

    def __init__(self, gpio, rev):
        super(PinKingModel, self).__init__()
        self.rev = rev
        try:
            self.layout = PIN_LAYOUT[rev]
        except KeyError as e:
            raise LayoutNotFoundError(e)

        self.selected_pin = 0
        self.directions = [None] * len(self.layout)
        self.out_values = [0] * len(self.layout)
        self.in_values = [0] * len(self.layout)
        self.gpio = gpio

        # set GPIO mode to board numbering
        self.gpio.setmode(self.gpio.BOARD)

        # set all pins to input
        for n in xrange(len(self.layout)):
            self.set_direction(n, self.gpio.IN)

        # read initial set of input values
        self.read_input_values()

    def set_direction(self, pin, direction):
        GPIO = self.gpio

        if self.layout[pin] in RESERVED_PINS:
            self.directions[pin] = None
            return

        prev_direction = self.directions[pin]
        self.directions[pin] = direction

        GPIO.setup(pin + 1, direction, pull_up_down=self.gpio.PUD_DOWN)

        if prev_direction != direction:
            self.direction_changed.send(self, pin=pin, direction=direction)

    def set_output_value(self, pin, value):
        prev_value = self.out_values[pin]
        self.out_values[pin] = value
        self.gpio.output(pin + 1, value)

        if prev_value != value:
            self.out_values_changed.send(self, values=self.out_values)

    def read_input_values(self):
        values = []

        IN = self.gpio.IN
        input = self.gpio.input

        for pin, direction in enumerate(self.directions):
            if direction == IN:
                values.append(input(pin + 1))
            else:
                values.append(None)

        if values != self.in_values:
            self.in_values = values
            self.in_values_changed.send(self, values=values)

    # def handle_keypress(self, keycode):
    #     # controller code, tacked onto model. sorry
    #     if keycode == ord('j') or keycode == curses.KEY_DOWN:
    #         self.selected_pin += 2
    #         self.selected_pin %= len(self.layout)
    #         self.notify()
    #         return True
    #     if keycode == ord('k') or keycode == curses.KEY_UP:
    #         self.selected_pin -= 2
    #         self.selected_pin %= len(self.layout)
    #         self.notify()
    #         return True
    #     if keycode == ord('h') or keycode == curses.KEY_LEFT:
    #         if self.selected_pin % 2:
    #             self.selected_pin -= 1
    #             self.selected_pin %= len(self.layout)
    #             self.notify()
    #         return True
    #     if keycode == ord(';') or keycode == curses.KEY_RIGHT:
    #         if not self.selected_pin % 2:
    #             self.selected_pin += 1
    #             self.selected_pin %= len(self.layout)
    #             self.notify()
    #         return True
    #     if keycode == ord('d'):
    #         old_dir = self.directions[self.selected_pin]
    #         if old_dir is not None:
    #             self.set_direction(
    #                 self.selected_pin,
    #                 GPIO.IN if old_dir == GPIO.OUT else GPIO.OUT
    #             )
    #             self.notify()
    #         else:
    #             curses.flash()
    #         return True
    #     if keycode == ord('t') or keycode == ord('\n'):
    #         if self.directions[self.selected_pin] == GPIO.OUT:
    #             self.set_output_value(
    #                 self.selected_pin,
    #                 GPIO.LOW if self.out_values[self.selected_pin] ==
    #                 GPIO.HIGH else GPIO.HIGH
    #             )
    #         return True
    #     if keycode == ord('r'):
    #         self.read_input_values()
    #         log.info(''.join(map(str, self.in_values)))
    #         return True

