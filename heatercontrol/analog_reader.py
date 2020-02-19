"""A Class to facilitate continual reading and averaging of
Labjack Analog inputs.
"""
import time
import threading
import traceback
import sys
import numpy as np

class AnalogChannel:
    """One analog channel and its associated ring buffer.
    """
    def __init__(self, lj_device, channel_number, long_settle=True, ring_buffer_size=20):
        """Parameters:
        lj_device:  The Labjack device object to read from, like a U3protected.
        channel_number: Channel number of the analog input.
        long_settle: If True use Long Settle mode of reading channel.
        ring_buffer_size: Number of elements to include in the ring buffer array.
        """
        self.lj_device = lj_device
        self.channel_number = channel_number
        self.long_settle = long_settle
        self.ring_buffer_size = ring_buffer_size
        self.ring_buffer = np.zeros(ring_buffer_size)
        self.first_read = True      # indicates no readings have occurred yet.
        self.ix = 0     # next index in ring buffer to fill out

    def read(self):
        """Reads the input and updates the ring buffer.  Returns the read value.
        """

        val = self.lj_device.get_analog(self.channel_number, self.long_settle)
        
        # if this is the first read, fill entire buffer with this value so a
        # sensible average will be computed
        if self.first_read:
            self.ring_buffer[:] = val
            self.first_read = False
        else:
            self.ring_buffer[self.ix] = val
        
        # update ring  buffer index, wrapping around if necessary
        self.ix = (self.ix + 1) % self.ring_buffer_size

        return val

    def value(self):
        """Returns the average value of the ring buffer.
        """
        return self.ring_buffer.mean()


class AnalogReader(threading.Thread):
    """Manages reading a set of Analog channels and returning a set of current
    average values from the readings.
    """

    def __init__(self, lj_device, channel_list, read_spacing=4.0, ring_buffer_size=20):
        """Parameters:
        lj_device:  Labjack device object such as U3protected or one with a similar interface.
        channel_list: List of channels to read.  Each channel is described by a two-tuple:
            (channel number, long settle boolean).  If long settle is True, then the
            channel will be read on the Labjack with Long Settle = True to allow for a
            higher source impedance.
            A sample list of channels would be:
                [
                    (14, True),        # channel 14, read with Long Settle
                    (16, False)        # channel 16, normal read length
                ] 
        read_spacing:  The number milliseconds of sleep in between Analog readings. This
            allows for other threads to access the Labjack device in between analog
            readings.
        ring_buffer_size: The number of readings to hold in a ring buffer for each channel.
            This ring buffer will be averaged to provide the final reading value of the channel.
            A larger ring buffer suppresses noise better but increases the response time of the
            returned channel value.

        Long Settle readings of analog channels on the Labjack U3 take about 4 milliseconds and
        allow for a source impendance of 200 K-ohms on the U3-LV.
        Normal readings take 0.7 milliseconds, but limit source impedance to 1OK on the U3-LV.
        For the U3-HV, the source impedance must always be 1 K-ohm or less.
        """

        # daemon thread so shuts down when program ends
        threading.Thread.__init__(self, daemon=True)

        self.channel_list = channel_list
        # Make a list of AnalogChannel objects
        self.channel_objects = [
            AnalogChannel(lj_device, ch, ls, ring_buffer_size) for ch, ls in channel_list
            ]
        self.read_spacing = read_spacing
        self.ring_buffer_size = ring_buffer_size

    def run(self):
        """Runs when the thread is started.  Starts the continual reading process.
        """
        # continually read analog inputs with a sleep gap between reads
        while True:
            for ch in self.channel_objects:
                try:
                    ch.read()
                except:
                    traceback.print_exc(file=sys.stdout)
                finally:
                    time.sleep(self.read_spacing / 1000.)


    def values(self):
        """Returns a dictionary of current channel values, keyed on channel number.
        Each current value is the average of the ring buffer for the channel.
        """
        values = {}
        for ch in self.channel_objects:
            try:
                values[ch.channel_number] = ch.value()
            except:
                traceback.print_exc(file=sys.stdout)
        
        return values
