"""Contains a class to implement a PWM output on a digital
channel of a Labjack Device.
"""
import threading
import sys
import time
import traceback

class PWM(threading.Thread):

    def __init__(
            self,
            lj_device,
            lj_channel,
            period,
            init_value = 0.0, 
        ):
        """Class to PWM a digital output on a Labjack device.  Operates in its
        own thread.
        Parameters:
        lj_device:  An object that provides a set_digital() method that writes
            to a Labjack digital output channel.  U3protected is an example type.
        lj_channel:  The channel number on the Labjack device to write to.
        period:  The period in seconds of full PWM cycle.
        init_value:  The inital value of the PWM duty-cycle, between 0.0 and 1.0
        """

        # daemon=True: will destroy thread when main thread ends
        threading.Thread.__init__(self, daemon=True)
        self.lj_device = lj_device
        self.lj_channel = lj_channel
        self.period = period
        self.value = init_value

    def run(self):
        """Call to start the thread and PWM process.
        Timinig is not perfect here due to not accounting for the time required
        to execute the Python statements. But, in normal circumstances, that is a
        short amount of time.
        """
        while True:
            try:
                if self.value != 0.0:
                    self.lj_device.set_digital(self.lj_channel, 1)
                    if self.value != 1.0:
                        # partial On
                        time.sleep(self.period * self.value)
                        self.lj_device.set_digital(self.lj_channel, 0)
                        time.sleep(self.period * (1.0 - self.value))
                    else:
                        # full On
                        time.sleep(self.period)
                else:
                    # full Off
                    self.lj_device.set_digital(self.lj_channel, 0)
                    time.sleep(self.period)

            except:
                traceback.print_exc(file=sys.stdout)
            
    def set_value(self, new_value):
        """Sets a new PWM value, between 0.0 and 1.0.
        """
        self.value = new_value
