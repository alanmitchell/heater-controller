"""Implements reading sensors and controlling the electric heater
for the Heat Pump Test Chamber.
"""

import time
import threading
from heatercontrol.U3protected import U3protected
from heatercontrol.pwm import PWM
from heatercontrol.analog_reader import AnalogReader

# Channel that reads the voltage that is applied to the
# thermistor circuits on the Labjack
THERMISTOR_APPLIED_V_CH = 15

# Delay in milliseconds between analog reads.  Should be long
# enough to give the PWM control a chance to break in.
ANALOG_READ_SPACING = 4.0     # milliseconds

# Number of elements in the ring buffer for each thermistor
# channel.
ANALOG_RING_BUFFER_SIZE = 20

# Divider resistor value used in Thermistor circuits
THERMISTOR_DIVIDER_R = 20000.0

class Controller(threading.Thread):

    def __init__(self,
            outer_temps,
            inner_temps,
            info_temps,
            control_period,
            pwm_channel,
            pwm_period,
            init_pid_p_param,
            init_pid_i_param,
            init_pid_d_param,
            results_callback,
        ):
        
        # daemon thread so it shuts down when program ends.
        threading.Thread.__init__(self, daemon=True)

        # save all of the function parameters
        self.outer_temps = outer_temps
        self.inner_temps = inner_temps
        self.info_temps = info_temps
        self.control_period = control_period
        self.pwm_channel = pwm_channel
        self.pwm_period = pwm_period
        self.pid_p_param = init_pid_p_param
        self.pid_i_param = init_pid_i_param
        self.pid_d_param = init_pid_d_param
        self.results_callback = results_callback
        self.max_pwm = 1.0

        analog_channel_list = []

        for label, channel, thermistor_type in outer_temps:
            analog_channel_list.append(channel)

        for label, channel, thermistor_type in inner_temps:
            analog_channel_list.append(channel)

        for label, channel, thermistor_type in info_temps:
            analog_channel_list.append(channel)

        # create and open the Labjack U3
        self.lj_dev = U3protected()

        # make the PWM controller and start it
        self.pwm = PWM(self.lj_dev, pwm_channel, pwm_period)
        self.pwm.start()

        # make and start the analog channel reader
        self.an_reader = AnalogReader(
            self.lj_dev, 
            analog_channel_list, 
            ANALOG_READ_SPACING, 
            ANALOG_RING_BUFFER_SIZE
        )
        self.an_reader.start()

    def set_control_parameters(self, 
            pid_p_param,
            pid_i_param,
            pid_d_param,
            max_pwm,
        ):
        self.pid_p_param = pid_p_param
        self.pid_i_param = pid_i_param
        self.pid_d_param = pid_d_param
        self.max_pwm = max_pwm

    def run(self):
        pass
