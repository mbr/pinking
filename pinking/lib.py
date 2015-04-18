import sys


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
