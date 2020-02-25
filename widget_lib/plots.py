"""Customized Plot Widgets.
"""

from pyqtgraph import PlotWidget
import pyqtgraph as pg

class SimplePlot(PlotWidget):

    def __init__(self, x_label, y_label, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Add Background colour to white
        self.setBackground('w')
        
        # Add Axis Labels
        self.setLabel('left', y_label, size=24)
        self.setLabel('bottom', x_label, size=24)

        # Add grid
        self.showGrid(x=True, y=True)

        #pen = pg.mkPen(color=(255, 0, 0), width=3)
        #self.plot(hour, temperature, name="Sensor 1",  pen=pen)
