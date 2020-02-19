#!/usr/bin/env python3

"""Tests the PWM feature of this application.
Outputs on FIO6 of the Labjack U3.

Takes a command line argument that give the PWM duty-cycle,
a value from 0.0 to 1.0.

Use Ctrl-C to stop the program.
""" 

import sys
import time

sys.path.insert(0, '../')
from heatercontrol.pwm import PWM
from heatercontrol.U3protected import U3protected

dev = U3protected()
value = float(sys.argv[1])
pwm = PWM(dev,
          lj_channel=6,
          period=2.0,
          init_value=value)
pwm.start()

try:
    while True:
        time.sleep(0.2)
finally:
    # shut off PWM channel
    pwm.set_value(0.0)
    dev.set_digital(6, 0)
