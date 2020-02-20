"""Implements reading sensors and controlling the electric heater
for the Heat Pump Test Chamber.
"""

import time
import threading
import traceback
import sys

import numpy as np
import simple_pid

from heatercontrol.U3protected import U3protected
from heatercontrol.pwm import PWM
from heatercontrol.analog_reader import AnalogReader
from heatercontrol.thermistor import Thermistor

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

def summarize_thermistor_group(thermistors, analog_readings):
    """Returns a dictionary summarizing the temperature values for a group
    of Thermistors.  The return dictionary has an "average" key that holds
    the average of the temperature values.  The return dictionary has a
    "detail" key that holds a list of two-tuples, one tuple for each Thermistor.
    The tuple data is (Thermistor label, temperature value in deg F).
    Parameters:
    thermistors:  A list of thermistor.Thermistor objects.
    analog_readings:  A dictionary of the voltage readings from the data
        acquisition device (usually Labjack).  The keys of the dictionary
        are channel numbers, and the values are voltages.
    """
    result = {'average': 0.0, 'detail': []}
    temps = []     # used to calculate average temperature
    for therm in thermistors:
        temp = therm.temperature(analog_readings)
        temps.append(temp)
        result['detail'].append( (therm.label, temp) )
    if len(temps):
        result['average'] = sum(temps) / len(temps)
    else:
        result['average'] = np.nan
    
    return result


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
            results_callback=None,
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
        self.results_callback = results_callback

        analog_channel_list = []
        self.outer_thermistors = []
        self.inner_thermistors = []
        self.info_thermistors = []

        for label, channel, thermistor_type in outer_temps:
            analog_channel_list.append(channel)
            self.outer_thermistors.append(
                Thermistor(thermistor_type, channel, THERMISTOR_APPLIED_V_CH, THERMISTOR_DIVIDER_R, label)
            )

        for label, channel, thermistor_type in inner_temps:
            analog_channel_list.append(channel)
            self.inner_thermistors.append(
                Thermistor(thermistor_type, channel, THERMISTOR_APPLIED_V_CH, THERMISTOR_DIVIDER_R, label)
            )

        for label, channel, thermistor_type in info_temps:
            analog_channel_list.append(channel)
            self.info_thermistors.append(
                Thermistor(thermistor_type, channel, THERMISTOR_APPLIED_V_CH, THERMISTOR_DIVIDER_R, label)
            )

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
        # delay to get at least the first reading in the readings ring buffer.
        time.sleep(0.5)

        # Make the PID controller object and set it's initial values
        self.pid = simple_pid.PID()
        self.set_control_parameters(
            init_pid_p_param, 
            init_pid_i_param,
            init_pid_d_param,
            1.0
        )

    def set_control_parameters(self, 
            pid_p_param,
            pid_i_param,
            pid_d_param,
            max_pwm,
        ):
        """Stores and sets the PID control parameters:
        pid_p_param:  P parameter
        pid_i_param:  I parameter
        pid_d_param:  D parameter
        max_pwm:      Max limit on PWM output, 0.0 - 1.0.
        """
        self.pid_p_param = pid_p_param
        self.pid_i_param = pid_i_param
        self.pid_d_param = pid_d_param
        self.max_pwm = min(max(0.0, max_pwm), 1.0)
        self.pid.tunings = (pid_p_param, pid_i_param, pid_d_param)
        self.pid.output_limits = (0.0, self.max_pwm)

    def turn_off_pwm(self):
        """Turns off the PWM output.  Used in shutdown or error situations.
        """
        try:
            self.pwm.set_value(0.0)
        except:
            pass
        
        # belt and suspenders:
        try:
            self.lj_dev.set_digital(self.pwm_channel, 0)
        except:
            pass

    def run(self):
        """Start and run the control process.
        """

        while True:

            try:
                # start a dictionary to hold all the temperature values and the PWM output
                vals = {}

                # get the analog readings
                readings = self.an_reader.values()

                # calculate inner chamber, outer chamber, and info tempertaure values
                vals['inner'] = summarize_thermistor_group(self.inner_thermistors, readings)
                vals['outer'] = summarize_thermistor_group(self.outer_thermistors, readings)
                vals['info'] = summarize_thermistor_group(self.info_thermistors, readings)

                # calculate the delta-temperature between inner and outer chamber and save
                # it in the vals dictionary.
                delta_t = vals['inner']['average'] -  vals['outer']['average']
                vals['delta_t'] = delta_t

                # calculate, use, and store the new output value from the PID controller object
                new_pwm = self.pid(delta_t)
                vals['pwm'] =  new_pwm
                self.pwm.set_value(new_pwm)

                # store a timestamp in vals
                vals['timestamp'] =  time.time() 

                # if there is a callback function to deliver the results to, call it.
                if self.results_callback:
                    self.results_callback(vals)

            except:
                traceback.print_exc(file=sys.stdout)
                # to be safe, shutdown PWM
                self.turn_off_pwm()

            finally:
                # This does not account for above processing time.  If that is not
                # short, recode to set an absolute time to wait for before proceeding.
                time.sleep(self.control_period)


