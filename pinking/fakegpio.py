import random
import time
import threading
from logbook import Logger


log = Logger('fakegpio')


class FakeGPIO(object):
    RPI_INFO = {
        'P1_REVISION': 3,
        'RAM': '1024M',
        'REVISION': 'a01041',
        'TYPE': 'Fake Pi2 Model B',
        'PROCESSOR': 'BCM2836',
        'MANUFACTURER': 'FakeGPIO'
    }

    BOARD = None
    IN = -1
    OUT = 1
    LOW = 0
    HIGH = 1
    PUD_UP = 21
    PUD_DOWN = 22

    def __init__(self):
        self.in_values = [0] * 40

        bg_thread = threading.Thread(target=self.rand_pins)
        bg_thread.daemon = True
        bg_thread.start()

    def rand_pins(self, delay=1):
        log.debug('Starting background thread for random pin io simulation.')
        while True:
            time.sleep(delay)
            self.change_random_input_pin()

    def change_random_input_pin(self):
        pin = random.randrange(len(self.in_values))

        self.in_values[pin] ^= 1

    def input(self, channel):
        return self.in_values[channel - 1]

    def __getattr__(self, name):
        def f(*args, **kwargs):
            parts = [str(a) for a in args]
            parts.extend('{}={}'.format(k, str(v)) for k, v in
                         kwargs.iteritems())
            log.debug('FakeGPIO: {}({})'.format(name, ', '.join(parts)))
        return f


GPIO = FakeGPIO()
