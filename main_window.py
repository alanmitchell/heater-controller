#!/usr/bin/env python3

"""The main GUI for the heater controller application.  Use the
PyQt5 framework or the GUI.
"""
import sys  
import os

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QMainWindow, QFormLayout)

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

from widget_lib.sliders import SliderWithVal

def make_graph():

    graphWidget = pg.PlotWidget()

    hour = [1,2,3,4,5,6,7,8,9,10]
    temperature = [30,32,34,32,33,31,29,32,35,45]

    # Add Background colour to white
    graphWidget.setBackground('w')

    # Add Title
    #graphWidget.setTitle("Graph Title") # , color='blue', size=18)
    
    # Add Axis Labels
    graphWidget.setLabel('left', 'Temperature (°F)', size=24)
    graphWidget.setLabel('bottom', 'Minute (0 = Now)', size=24)

    # Add legend
    graphWidget.addLegend()

    # Add grid
    graphWidget.showGrid(x=True, y=True)

    # Set Range
    graphWidget.setXRange(0, 10, padding=0.05)
    graphWidget.setYRange(20, 55, padding=0)

    pen = pg.mkPen(color=(255, 0, 0), width=3)
    graphWidget.plot(hour, temperature, name="Sensor 1",  pen=pen)

    return graphWidget

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.graphWidget1 = make_graph()
        self.graphWidget2 = make_graph()
        self.graphWidget3 = make_graph()
        
        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.graphWidget1)
        graph_layout.addWidget(self.graphWidget2)
        graph_layout.addWidget(self.graphWidget3)

        controls = QWidget()
        controls.setFixedWidth(250)
        controls.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        control_layout = QVBoxLayout()
        control_layout.addWidget(QCheckBox('Enable Heater'))

        control_layout.addSpacing(10)
        pid_group = QGroupBox('PID Tuning Parameters')
        pid_form = QFormLayout()
        pid_form.addRow("P", SliderWithVal((0.3, 3.0), 2.0, 2))
        pid_form.addRow("I", SliderWithVal((0.0, 0.2), 0.05, 3))
        pid_form.addRow("D", SliderWithVal((0.0, 1.0), 0.0, 2))
        pid_group.setLayout(pid_form)
        control_layout.addWidget(pid_group)

        control_layout.addSpacing(10)
        control_layout.addWidget(QLabel('Maximum Heater Output\n(% of Full Capacity)'))
        control_layout.addWidget(SliderWithVal((0.0, 1.0), 1.0, 2))

        control_layout.addSpacing(10)
        control_layout.addWidget(QCheckBox('Enable Simple On/Off Control'))

        control_layout.addSpacing(10)
        control_layout.addWidget(QLabel('Current Log File:\n2020-02-23_234410.log'))
        control_layout.addWidget(QPushButton('Start New Log File'))

        control_layout.addStretch(1)

        controls.setLayout(control_layout)

        main_layout = QHBoxLayout()
        main_layout.addWidget(controls)
        main_layout.addLayout(graph_layout)
        self.setLayout(main_layout)

        self.setGeometry(1000, 800, 1000, 800)
 
def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__=='__main__':
    main()
