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
THERMISTOR_DIVIDER_R = 9760.0

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
        result['detail'].append( (therm.label, round(temp, 2)) )
    if len(temps):
        result['average'] = round(sum(temps) / len(temps), 2)
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
            init_pwm_max,
            init_pid_tunings,
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
            analog_channel_list.append((channel, True))
            self.outer_thermistors.append(
                Thermistor(thermistor_type, channel, THERMISTOR_APPLIED_V_CH, THERMISTOR_DIVIDER_R, label)
            )

        for label, channel, thermistor_type in inner_temps:
            analog_channel_list.append((channel, True))
            self.inner_thermistors.append(
                Thermistor(thermistor_type, channel, THERMISTOR_APPLIED_V_CH, THERMISTOR_DIVIDER_R, label)
            )

        for label, channel, thermistor_type in info_temps:
            analog_channel_list.append((channel, True))
            self.info_thermistors.append(
                Thermistor(thermistor_type, channel, THERMISTOR_APPLIED_V_CH, THERMISTOR_DIVIDER_R, label)
            )

        # Added in the thermistor applied voltage channel to the channel list.  It
        # has good source impedance so does not need long settling.
        analog_channel_list.append((THERMISTOR_APPLIED_V_CH, False))

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
        self.pid_tunings = init_pid_tunings
        self.pwm_max = init_pwm_max
        self.enable_on_off_control = False
        self.enable_control = False

    @property
    def pid_tunings(self):
        return self.pid.tunings
        
    @pid_tunings.setter
    def pid_tunings(self, params):
        self.pid.tunings = params    # set tunings into PID object.

    @property
    def pwm_max(self):
        return self._pwm_max

    @pwm_max.setter
    def pwm_max(self, val):
        self._pwm_max = min(max(0.0, val), 1.0)
        self.pid.output_limits = (0.0, self._pwm_max)

    @property
    def enable_control(self):
        return self._enable_control
    
    @enable_control.setter
    def enable_control(self, bool_val):
        self._enable_control = bool_val

    @property
    def enable_on_off_control(self):
        return self._enable_on_off_control

    @enable_on_off_control.setter
    def enable_on_off_control(self, bool_val):
        self._enable_on_off_control = bool_val

    @property
    def current_results(self):
        """Returns a dictionary of the most current inputs and outputs from the controller.
        """
        return self._current_results
        
    def reset_pid(self):
        """Resets PID state parameters.
        """
        self.pid.reset()

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
                vals['delta_t'] = round(delta_t, 2)

                # calculate, use, and store the new output value from the PID controller object
                if self.enable_control:
                    if self.enable_on_off_control:
                        new_pwm = self.pwm_max if delta_t < 0 else 0.0    # simple On/Off control
                    else:
                        new_pwm = self.pid(delta_t)
                    vals['pwm'] =  round(new_pwm, 3)
                    self.pwm.set_value(new_pwm)
                else:
                    vals['pwm'] = 0.0
                    self.pwm.set_value(0.0)

                # store a timestamp in vals
                vals['timestamp'] =  round(time.time(), 3)

                # save this as an attribute
                self._current_results = vals

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
