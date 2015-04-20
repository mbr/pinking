# new logging handler using a deque

__version__ = '0.1.dev1'


from collections import deque
from threading import RLock

import logbook


class NullHandler(logbook.NullHandler):
    blackhole = False


class RingBufferHandler(logbook.Handler, logbook.StringFormatterHandlerMixin):
    def __init__(self, maxlen=None, format_string=None, *args, **kwargs):
        super(RingBufferHandler, self).__init__(*args, **kwargs)
        logbook.StringFormatterHandlerMixin.__init__(self, format_string)
        self.buffer = deque(maxlen=maxlen)
        self._lock = RLock()

    def emit(self, record):
        rec = self.formatter.format_record(record, self)
        with self._lock:
            # while append is thread-safe, the list(deque) in get_message()
            # is not!
            self.buffer.append(rec)

    def get_message(self):
        with self._lock:
            return list(self.buffer)

handler = RingBufferHandler()
handler.push_application()

logbook.debug('initial log message')

# construct some sample model

from pinking.model import PinKingModel, RESERVED_PINS
from pinking.fakegpio import FakeGPIO

gpio = FakeGPIO()

# some set to HIGH
gpio.in_values[32] = gpio.HIGH
gpio.in_values[35] = gpio.HIGH
gpio.in_values[39] = gpio.HIGH

model = PinKingModel(gpio, gpio.RPI_INFO['REVISION'])


import urwid


palette = [
    # selected: standout
    # in/out: label+pin green/red, background black
    # low/high: background green/red, foreground black
    ('pin_in_low', 'light green', 'black'),
    ('pin_in_high', 'white', 'dark green'),
    ('label_selected', 'black', 'light gray'),
    ('label_unselect', 'white', 'black'),

    ('pin_special', 'brown', 'black'),
    ('label_special', 'brown', 'black'),
]


class PinDisplayWidget(urwid.Widget):
    _sizing = frozenset(['fixed'])
    pfmt = '[{:2}]'

    def __init__(self, model):
        super(PinDisplayWidget, self).__init__()
        self.model = model
        self.update_dimensions()
        self.active_pin = 30

    def update_dimensions(self):
        length = len(self.model.layout)
        self.layout_height = length / 2 + length % 2

        # width of the text of a label
        self.largest_label = max(len(l) for l in self.model.layout)

        self.lfmt = ('{:>%d} ' % self.largest_label,
                     ' {:<%d}' % self.largest_label)

        # width of label text + padding
        self.label_width = max(len(f.format('')) for f in self.lfmt)

        # width of a rendered pin
        self.pin_width = len(self.pfmt.format(0))
        self.pin_gap = 3

        # calculate total width
        self.layout_width = (
            self.label_width + self.pin_width + self.pin_gap +
            self.pin_width + self.label_width

        )

    def pack(self, size=None, focus=False):
        return (self.layout_width, self.layout_height)

    def render(self, size, focus=False):
        canv = urwid.CompositeCanvas(urwid.SolidCanvas(' ',
                                                       self.layout_width,
                                                       self.layout_height))

        def draw_chars(chars, left, top, attr=None):
            cc = urwid.CompositeCanvas(urwid.TextCanvas([chars]))

            if attr:
                cc.fill_attr(attr)

            canv.overlay(cc, left, top)

        for pin, name in enumerate(self.model.layout):
            row = pin // 2
            col = pin % 2

            # direction
            pdir = self.model.directions[pin]
            value = None

            gpio = self.model.gpio

            if pdir == gpio.IN:
                value = self.model.in_values[pin]
            elif pdir == gpio.OUT:
                value = self.model.out_values[pin]

            # construct the attribute tag
            pin_tag = 'pin_{}_{}'.format(
                'in' if pdir == gpio.IN else 'out',
                'low' if value == gpio.LOW else 'high',
            ) if name not in RESERVED_PINS else 'pin_special'

            label_tag = 'label_{}'.format(
                'selected' if pin == self.active_pin else 'unselected',
            ) if name not in RESERVED_PINS else 'label_special'

            label = self.lfmt[col].format(name)
            draw_chars(label,
                       col * (2 * self.pin_width + self.pin_gap +
                              self.label_width),
                       row,
                       label_tag)

            draw_chars(self.pfmt.format(pin + 1),
                       self.label_width + col * (self.pin_width +
                                                 self.pin_gap),
                       row,
                       pin_tag)

        return canv


layout = urwid.ListBox(urwid.SimpleFocusListWalker([
    urwid.Padding(PinDisplayWidget(model), width='clip', align='center'),
    urwid.Text('log goes here'),
]))

mw = urwid.Frame(layout,
                 urwid.Text('pinking {}'.format(__version__),
                            align='center',
                            wrap='clip',),
                 urwid.Text('World'))

loop = urwid.MainLoop(mw, palette)
loop.run()
