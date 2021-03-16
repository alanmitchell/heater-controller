"""Contains a class to facilitate calculation of a rolling average.
"""

class RollingAverage:

    def __init__(self, max_period):
        """Parameters:
           max_period: maximum number of periods to include in the rolling average.
              When the total reading count is less than this, only the available number
              of readings are included in the average.
        """
        self.max_period = max_period
        self.values = []
        self.ix = 0         # next index in the list to use.

    def add_reading(self, val):
        """Adds the reading "val" to the computation of the rolling average.
        Returns the new rolling average.
        """
        if len(self.values) < self.max_period:
            # haven't reach the maximum number of periods yet, so increase
            # the size of the list
            self.values.append(val)
        
        else:
            # list is maxed out, so treat it like a ring buffer.
            self.values[self.ix] = val
            self.ix = (self.ix + 1) % self.max_period

        return sum(self.values) / len(self.values)
        