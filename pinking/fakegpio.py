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

    def __getattr__(self, name):
        def f(*args):
            log.debug('FakeGPIO: {}({})'.format(name, ', '.join(
                map(str, args)))
            )
        return f



GPIO = FakeGPIO()
