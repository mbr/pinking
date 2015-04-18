from contextlib import contextmanager
import curses


@contextmanager
def curses_wrap():
    # mostly copied from Python's Lib/curses/__init__.py

    stdscr = curses.initscr()

    # Turn off echoing of keys, and enter cbreak mode,
    # where no buffering is performed on keyboard input
    curses.noecho()
    curses.cbreak()

    # In keypad mode, escape sequences for special keys
    # (like the cursor keys) will be interpreted and
    # a special value like curses.KEY_LEFT will be returned
    stdscr.keypad(1)

    # Start color, too.  Harmless if the terminal doesn't have
    # color; user can test with has_color() later on.  The try/catch
    # works around a minor bit of over-conscientiousness in the curses
    # module -- the error return from C start_color() is ignorable.
    try:
        curses.start_color()
    except:
        pass

    yield stdscr

    stdscr.keypad(0)
    curses.echo()
    curses.nocbreak()
    curses.endwin()
