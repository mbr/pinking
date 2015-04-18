import curses
import threading
from Queue import Queue
import sys

from logbook import Logger


log = Logger('ui')


class AppController(object):
    def handle_keypress(self, keycode):
        if keycode == ord('q'):
            sys.exit(0)


class Widget(object):
    needs_redraw = False
    widgets = []

    def __init__(self):
        self.widgets.append(self)

    def update(self):
        self.needs_redraw = True

    def redraw(self):
        self.draw()
        self.needs_redraw = False

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


class PinKingUI(Widget):
    def __init__(self, scr, model):
        super(PinKingUI, self).__init__()

        self.scr = scr
        self.model = model
        self.events = Queue()

        # start listening to keyboard events
        key_thread = threading.Thread(target=self._read_keypress)
        key_thread.daemon = True
        key_thread.start()

        # turn off cursor
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()

        # init cursor colors
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        curses.init_pair(7, curses.COLOR_WHITE, -1)

        self.ctrls = [
            AppController(),
            self.model,
        ]

        # instantiate ui windows
        PinWindow.from_model(pm)

        # add logging window
        LogWindow(curses.newwin(self.height - pw.height - 1,
                                self.width,
                                pw.height + 1,
                                0))

    def run(self):
        log.debug('Starting event loop...')

        while True:
            # redraw all widgets that need redrawing
            for widget in self.widgets:
                widget.redraw()

            # get next event
            ev = self.events.get()

            if 'keypress' == ev[0]:
                keycode = ev[1]

                # let any controller handle the keypress
                for c in self.ctrls:
                    if c.handle_keypress(keycode):
                        continue
            else:
                raise RuntimeError('Received unexpected event {}'.format(ev))

    def _read_keypress(self):
        scr, q = self.scr, self.events

        while True:
            ch = scr.getch()

            if ch is not -1:
                q.put(('keypress', ch))

    @classmethod
    def create_and_run(cls, *args, **kwargs):
        return cls(*args, **kwargs).run()
