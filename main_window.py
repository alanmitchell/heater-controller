#!/usr/bin/env python3

"""The main GUI for the heater controller application.  Use the
PyQt5 framework or the GUI.
"""
import sys  
import os
import time
from pprint import pprint

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox,
        QGroupBox, QHBoxLayout, QVBoxLayout, QLabel,
        QPushButton, QSizePolicy,
        QVBoxLayout, QWidget, QFormLayout)

from widget_lib.sliders import SliderWithVal
from widget_lib.plots import SimplePlot

import user.settings as stng
from heatercontrol.controller import Controller

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.plotDelta = SimplePlot('Minute (0 = Now)', 'Inner - Outer Temp (°F)')
        self.plotHeater = SimplePlot('Minute (0 = Now)', 'Heater Output, % of Max')
        self.plotHeater.setYRange(0.0, 1.03, padding=0)
        self.plotTemperature = SimplePlot('Minute (0 = Now)', 'Temperature (°F)')
        self.plotTemperature.addLegend()
        
        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.plotDelta)
        graph_layout.addWidget(self.plotHeater)
        graph_layout.addWidget(self.plotTemperature)

        controls = QWidget()
        controls.setFixedWidth(250)
        controls.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        control_layout = QVBoxLayout()
        control_layout.addWidget(QCheckBox('Enable Heater'))

        # get the PID parameter ranges from the settings file.
        kp_min, kp_init, kp_max = stng.PID_P
        ki_min, ki_init, ki_max = stng.PID_I
        kd_min, kd_init, kd_max = stng.PID_D

        control_layout.addSpacing(10)
        pid_group = QGroupBox('PID Tuning Parameters')
        pid_form = QFormLayout()
        self.slider_kp = SliderWithVal((kp_min, kp_max), kp_init, 2)
        self.slider_ki = SliderWithVal((ki_min, ki_max), ki_init, 3)
        self.slider_kd = SliderWithVal((kd_min, kd_max), kd_init, 2)
        pid_form.addRow("P", self.slider_kp)
        pid_form.addRow("I", self.slider_ki)
        pid_form.addRow("D", self.slider_kd)
        pid_group.setLayout(pid_form)
        control_layout.addWidget(pid_group)
        # handle change in PID tuning sliders
        self.slider_kp.valueChanged.connect(self.pid_tuning_change)
        self.slider_ki.valueChanged.connect(self.pid_tuning_change)
        self.slider_kd.valueChanged.connect(self.pid_tuning_change)

        control_layout.addSpacing(10)
        self.slider_heater_max = SliderWithVal((0.0, 1.0), stng.INIT_PWM_MAX, 2)
        self.slider_heater_max.valueChanged.connect(self.heater_max_change)
        control_layout.addWidget(QLabel('Maximum Heater Output\n(% of Full Capacity)'))
        control_layout.addWidget(self.slider_heater_max)

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

        self.controller = Controller(
            stng.OUTER_TEMPS,
            stng.INNER_TEMPS,
            stng.INFO_TEMPS,
            stng.CONTROL_PERIOD,
            stng.PWM_CHANNEL,
            stng.PWM_PERIOD,
            stng.INIT_PWM_MAX,
            (kp_init, ki_init, kd_init),
            self.handle_control_results
        )
        self.controller.enable_control = True
        self.controller.start()

    def closeEvent(self, event):
        # Turn off heater when this window is closed.
        self.controller.turn_off_pwm()

    def pid_tuning_change(self, _):
        """One of the PID tuning sliders changed.
        """
        tunings = (self.slider_kp.value, self.slider_ki.value, self.slider_kd.value)
        self.controller.pid_tunings = tunings

    def heater_max_change(self, _):
        self.controller.pwm_max = self.slider_heater_max.value

    def handle_control_results(self, vals):

        print(f"Delta-T: {vals['delta_t']:.2f} F, PWM: {vals['pwm']:.3f}")


def main():
    app = QApplication(sys.argv)
    main = MainWindow()
    #main.slider_kd.setEnabled(False)
    main.move(0, 0)
    main.show()

    try:
        sys.exit(app.exec_())

    finally:
        # make sure Heater is turned off
        main.controller.turn_off_pwm()

if __name__=='__main__':
    main()
