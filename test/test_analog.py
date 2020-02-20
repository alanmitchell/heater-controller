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
    (0, False),
    (1, True),
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

while True:
    readings = rdr.values() 
    print(readings)
    print(f'{t.temperature(readings):.2f} F')
    time.sleep(1.7)
