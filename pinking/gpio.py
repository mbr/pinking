is_fake = False

try:
    import RPi.GPIO as GPIO
except ImportError:
    is_fake = True

    from . import fakegpio as GPIO
