import sys

if sys.version_info.major == 2:
    PKG_NAMES = {
        'RPi.GPIO': 'python-rpi.gpio',
    }
elif sys.version_info.major == 3:
    PKG_NAMES = {
        'RPi.GPIO': 'python3-rpi.gpio',
    }
else:
    PKG_NAMES = {}


PI_MODELS = {
    # from http://www.raspberrypi-spy.co.uk/2012/09/
    #      checking-your-raspberry-pi-board-version/
    '0002': 'RPi1_B_1.0_256',
    '0003': 'RPi1_B_1.0_ECN0001_256',
    '0004': 'RPi1_B_2.0_256',
    '0005': 'RPi1_B_2.0_256',
    '0006': 'RPi1_B_2.0_256',
    '0007': 'RPi1_A_256',
    '0008': 'RPi1_A_256',
    '0009': 'RPi1_A_256',
    '000d': 'RPi1_B_2.0_512',
    '000e': 'RPi1_B_2.0_512',
    '000f': 'RPi1_B_2.0_512',
    '0010': 'RPi1_B+_512',
    '0011': 'RPi1_Compute_Module_512',
    '0012': 'RPi1_A+_256',
    'a01041': 'Rpi2_B_UK_1024',
    'a21041': 'Rpi2_B_China_1024',
}


PIN_LAYOUT = {
    # http://www.element14.com/community/docs/DOC-73950
    # /l/raspberry-pi-2-model-b-gpio-40-pin-block-pinout
    'Rpi2_B_UK_1024': [
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

# aliases:
PIN_LAYOUT['Rpi2_B_China_1024'] = PIN_LAYOUT['Rpi2_B_UK_1024']
