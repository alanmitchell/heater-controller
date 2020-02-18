"""Provides a thread-safe access to a Labjack U3 for reading analog channels
and writing digital channels.
"""

import time
import u3

class U3protected:

    def __init__(self, timeout=0.1):
        """Opens U3 and performs initialization tasks.
        Parameters:
        timeout:  Determines how long access will be tried before timing out
            due to an existing lock on the device.
        """

        self.timeout =timeout
        self.dev = u3.U3()    # open U3
        self.dev.getCalibrationData()   # get the calibration data

        # This is the variable that will control access to the U3.
        # If True, device is locked (in use).
        self.access_lock = False

    def __del__(self):
        """Close the U3 when this object is destroyed.
        """
        self.dev.close()

    def acquire_lock(self):
        """Waits for the device lock to be released and then sets it.
        Raises an error if wait times out.
        """
        st = time.time()
        while self.access_lock:
            if time.time() - st > self.timeout:
                raise ValueError('Timed out waiting for access to U3 device.')
            time.sleep(0.001)    # delay 1 ms
        
        # set lock
        self.access_lock = True

    def get_analog(self, channel, long_settle=True):
        """Returns the voltage reading from an Analog channel.
        Parameters:
        long_settle: If True uses the Long Settle mode of reading which
            allows for a much higher source impedance from the voltage source
            being measured.
        """
        # wait for the lock
        self.acquire_lock()

        try:
            return self.dev.getAIN(channel, longSettle=long_settle)
        
        finally:
            # always release lock
            self.access_lock = False
        
    def set_digital(self, channel, state):

        # wait for the lock
        self.acquire_lock()

        try:
            return self.dev.setDOState(channel, state)

        finally:
            # always release lock
            self.access_lock = False
