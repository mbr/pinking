import curses
import threading
from Queue import Queue
import sys

from logbook import Logger

from lib import PIN_LAYOUT


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


def PinKingUI(Widget):
    def __init__(self, scr, rev):
        super(PinKingUI, self).__init__()

        self.scr = scr
        self.rev = rev
        self.events = Queue()

        # start listening to keyboard events
        key_thread = threading.Thread(target=self.read_keypresses),
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
