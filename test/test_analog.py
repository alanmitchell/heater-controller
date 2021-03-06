#!/usr/bin/env python3

"""Tests the Analog Reading classes, and also runs the PWM concurrently.
"""

import sys
import time

sys.path.insert(0, '../')
from heatercontrol.analog_reader import AnalogReader
from heatercontrol.U3protected import U3protected
from heatercontrol.pwm import PWM
from heatercontrol.thermistor import Thermistor

dev = U3protected()

ch_list = [
    (1, True),
    (3, True),
    (8, True),
    (15, False),
]
rdr = AnalogReader(dev, ch_list)
rdr.start()

# run the PWM simultaneously to test joint use.
pwm = PWM(dev,
          lj_channel=6,
          period=2.0,
          init_value=0.5)
pwm.start()

t = Thermistor('BAPI 10K-3', 8, 15, 9760)
time.sleep(0.1)

try:
    while True:
        readings = rdr.values()
        lin = f'{readings} {t.temperature(readings):.2f} F'
        print(lin)
        time.sleep(1.7)

finally:
    # shut off PWM channel
    print('Closing down...')
    pwm.set_value(0.0)
    dev.set_digital(6, 0)
