#! /usr/bin/python2

import time
import sys

EMULATE_HX711=False

referenceUnit = -1

if not EMULATE_HX711:
    import RPi.GPIO as GPIO
    from hx711 import HX711
else:
    from emulated_hx711 import HX711

def cleanAndExit():
    print("Cleaning...")

    if not EMULATE_HX711:
        GPIO.cleanup()

    print("Bye!")
    sys.exit()

hx = HX711(6, 2)
hx.set_reference_unit(referenceUnit)
hx.reset()

hx.tare()

print("Tare done! Add weight now...")

def func():
    while True:
        try:
            val = hx.get_weight(5)
            yield val
            hx.power_down()
            hx.power_up()
            time.sleep(0.1)

        except (KeyboardInterrupt, SystemExit):
            cleanAndExit()

function = func()
for i in function:
    print(i)
