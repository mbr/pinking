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
    PUD_UP = 1
    PUD_DOWN = 0

    def __getattr__(self, name):
        def f(*args, **kwargs):
            parts = [str(a) for a in args]
            parts.extend('{}={}'.format(k, str(v)) for k, v in
                         kwargs.iteritems())
            log.debug('FakeGPIO: {}({})'.format(name, ', '.join(parts)))
        return f


GPIO = FakeGPIO()
