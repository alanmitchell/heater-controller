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
pwm = PWM(dev, 6, 2.0)

value = float(sys.argv[1])
pwm.set_value(value)
while True:
    time.sleep(0.1)
