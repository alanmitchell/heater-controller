#!/usr/bin/env python3
"""This is just a non-GUI test script!!
Expects a settings.py file in the user/ folder, with the structure
of 'settings_example.py' found in this folder.
"""
import time
from pprint import pprint
import user.settings as stng
from heatercontrol.controller import Controller

def handle_control_results(vals):
    """This callback function is called by the controller object and
    the controller provides the dictionary 'vals', which contains sensor
    and output values. 
    """
    pprint(vals)
    print(f"Delta-T: {vals['delta_t']:.2f} F, PWM: {vals['pwm']:.3f}")

if __name__=='__main__':

    # get the PID parameter ranges from the settings file.
    kp_min, kp_init, kp_max = stng.PID_P
    ki_min, ki_init, ki_max = stng.PID_I
    kd_min, kd_init, kd_max = stng.PID_D

    # get the outer temperature averaging duration from the settings file, but
    # if not present (recent addition to settings file), assume no averaging.
    outer_avg_duration = stng.OUTER_AVG_SECONDS if hasattr(stng, 'OUTER_AVG_SECONDS') else None

    #  make a controller object
    controller = Controller(
        stng.OUTER_TEMPS,
        stng.INNER_TEMPS,
        stng.INFO_TEMPS,
        stng.THERMISTOR_DIVIDER_R,
        stng.THERMISTOR_APPLIED_V_CH,
        stng.CONTROL_PERIOD,
        outer_avg_duration,
        stng.PWM_CHANNEL,
        stng.PWM_PERIOD,
        stng.INIT_PWM_MAX,
        (kp_init, ki_init, kd_init),
        handle_control_results
    )
    controller.enable_control = True
    controller.enable_on_off_control = False
    controller.start()
    
    try:
        while True:
            time.sleep(1.0)
    
    finally:
        # Make sure PWM is turned off when program exits.
        controller.turn_off_pwm()
