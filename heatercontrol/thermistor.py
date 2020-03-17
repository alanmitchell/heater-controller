#!/usr/bin/env python3
"""
Class to convert Thermistor readings into temperatures. Also has a
class method that determines an unknown resistance in a divider
network.
"""

from math import log

# Steinhart-Hart Coefficients for various thermistors
coeff = {
'Tekmar 071': (0.001124476, 0.00023482, 8.54409E-08),
'Sure 10K': (0.00090296, 0.000249878, 1.9712E-07),
'US Sensor 5K': (0.00128637, 0.00023595, 9.3841E-08),
'US Sensor J': (0.001128437, 0.000234244, 8.71364E-08),
'BAPI 10K-3': (0.001028172, 0.0002392811, 1.5611865E-07),
'InOut': (0.00131413, 0.000174074, 5.576999E-07),
'Quality 10K Z': (0.001125161025848, 0.000234721098632, 8.5877049E-08),
'ACR': (0.00105135, 0.0002475590, 2.8879777e-08),
'Quality 10K S': (0.001028267, 0.000239267, 1.561795e-07),
'TDK 5K': (0.001020977743, 0.000263446501, 1.444025e-07),
}

class Thermistor:

    def __init__(self, therm_name, therm_ch, applied_ch, divider_r, label='', acq_dev_id=''):
        '''
        'therm_name' identifies the thermistor type and is the key into 
            the coefficient dictionary (coeff)
        'therm_ch': the channel number key into the readings dictionary that
            gives the voltage read on the thermistor input.
        'applied_ch': the channel number key into the readings dictionry that
            gives the voltage applied to the thermistor divider network.
        'divider_r' is the resistance in ohms of the fixed divider resistor.
        'label': is a text label to identify the sensor and does not affect calcs.
        'acq_dev_id': a string that identifies which data acquisition device the
            thermistor is connected to.  Does not affect calculations.
        '''
        self.coeff = coeff[therm_name]
        self.therm_name = therm_name
        self.therm_ch = therm_ch
        self.applied_ch = applied_ch
        self.divider_r = divider_r
        self.label = label

    def temperature(self, readings, unit='F'):
        """Returns the thermistor temperature given a dictionary of voltage
        readings 'readings'.  Object properties give the channel numbers for
        the thermistor voltage and the applied voltage, which are found in the
        'readings' dictionary.  An object property also gives the divider resistor
        resistance.
        """
        therm_v = readings[self.therm_ch]
        applied_v = readings[self.applied_ch]
        return self.TfromV(therm_v, applied_v, unit)

	
    def TfromR(self, resis, unit='F'):
        """
        Returns temperature from a thermistor resistance in ohms.  'unit' can be 'F' or 'C'
        for Fahrenheit or Celsius.
        """
        C1 = self.coeff[0]
        C2 = self.coeff[1]
        C3 = self.coeff[2]
        lnR = log(resis) if resis>0.0 else -9.99e99
        temp_f = (1.8 / (C1 + C2 * lnR + C3 * lnR ** 3)) - 459.67
        if unit=='F':
            return temp_f
        else:
            return (temp_f - 32.0)/1.8

    def TfromV(self, measured_v, applied_v=None, unit='F'):
        """
        Returns a temperature given a measured voltage from a divider network,
        If 'applied_v', the voltage applied to the divider network, is given, the 
        applied voltage supplied in the constructor of this class is overridden.
        'unit' can be 'F' (Fahrenheit) or 'C' (Celsius).
        """
        resis = self.RfromV(measured_v, applied_v)
        return self.TfromR(resis, unit)
    	
    def RfromV(self, measured_v, applied_v):
        """
        Returns resistance when given a measured voltage (or A/D count) from a 
        divider circuit with divider resistance 'self.divider_r'. 'applied_v' is the 
        voltage (or A/D count) applied to the divider network.
        """
        div_v = applied_v - measured_v
        # protect against divide by 0
        if div_v>0:
            return measured_v/div_v * self.divider_r
        else:
            return 9.99e99   # something very big
