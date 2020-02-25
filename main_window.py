#!/usr/bin/env python3

"""The main GUI for the heater controller application.  Use the
PyQt5 framework or the GUI.
"""
import sys  
import os
import time
from datetime import datetime
from pprint import pprint

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox,
        QGroupBox, QHBoxLayout, QVBoxLayout, QLabel,
        QPushButton, QSizePolicy, QMessageBox,
        QVBoxLayout, QWidget, QFormLayout)
import pyqtgraph as pg
import numpy as np

from widget_lib.sliders import SliderWithVal
from widget_lib.plots import SimplePlot

import user.settings as stng
from heatercontrol.controller import Controller

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # get the PID parameter ranges from the settings file.
        kp_min, kp_init, kp_max = stng.PID_P
        ki_min, ki_init, ki_max = stng.PID_I
        kd_min, kd_init, kd_max = stng.PID_D

        # remember the initial values so they can be retrieved for a PID reset
        self.kp_init = kp_init
        self.ki_init = ki_init
        self.kd_init = kd_init

        #  make a controller object
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

        self.plotDelta = SimplePlot('Minute (0 = Now)', 'Inner - Outer Temp (°F)')
        self.plotPWM = SimplePlot('Minute (0 = Now)', 'Heater Output, % of Max')
        self.plotPWM.setYRange(0.0, 1.03, padding=0)
        self.plotTemperature = SimplePlot('Minute (0 = Now)', 'Temperature (°F)')
        self.plotTemperature.addLegend()
        
        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.plotDelta)
        graph_layout.addWidget(self.plotPWM)
        graph_layout.addWidget(self.plotTemperature)

        controls = QWidget()
        controls.setFixedWidth(250)
        controls.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        control_layout = QVBoxLayout()

        self.check_enable_heater = QCheckBox('Enable Heater')
        self.check_enable_heater.stateChanged.connect(self.enable_heater_change)
        self.enable_heater_change()
        control_layout.addWidget(self.check_enable_heater)

        control_layout.addSpacing(20)
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

        self.button_reset_pid = QPushButton('Restore Initial PID Tunings')
        self.button_reset_pid.clicked.connect(self.ask_reset_pid)
        control_layout.addWidget(self.button_reset_pid)

        control_layout.addSpacing(20)
        self.slider_heater_max = SliderWithVal((0.0, 1.0), stng.INIT_PWM_MAX, 2)
        self.slider_heater_max.valueChanged.connect(self.heater_max_change)
        control_layout.addWidget(QLabel('Maximum Heater Output\n(% of Full Capacity)'))
        control_layout.addWidget(self.slider_heater_max)

        control_layout.addSpacing(20)
        self.check_enable_on_off = QCheckBox('Enable Simple On/Off Control')
        self.check_enable_on_off.stateChanged.connect(self.enable_on_off_change)
        self.enable_on_off_change()
        control_layout.addWidget(self.check_enable_on_off)

        control_layout.addSpacing(20)
        self.label_log_name = QLabel('')
        control_layout.addWidget(self.label_log_name)
        self.button_start_new_log = QPushButton('Start New Log File')
        self.button_start_new_log.clicked.connect(self.ask_new_log_file)
        control_layout.addWidget(self.button_start_new_log)
        self.start_new_log_file()

        control_layout.addStretch(1)

        controls.setLayout(control_layout)

        main_layout = QHBoxLayout()
        main_layout.addWidget(controls)
        main_layout.addLayout(graph_layout)
        self.setLayout(main_layout)

        self.setGeometry(1000, 800, 1000, 800)
        self.setWindowTitle('Heater Controller')

        # the current index into the logging arrays
        self.log_ix = 0

        # Start the controller
        self.controller.start()

    def closeEvent(self, event):
        # Turn off heater when this window is closed.
        self.controller.turn_off_pwm()

    def enable_heater_change(self):
        self.controller.enable_control = self.check_enable_heater.isChecked()

    def enable_on_off_change(self):
        self.controller.enable_on_off_control = self.check_enable_on_off.isChecked()
        self.controller.reset_pid()

    def pid_tuning_change(self, _):
        """One of the PID tuning sliders changed.
        """
        tunings = (self.slider_kp.value, self.slider_ki.value, self.slider_kd.value)
        self.controller.pid_tunings = tunings

    def heater_max_change(self, _):
        self.controller.pwm_max = self.slider_heater_max.value

    def ask_new_log_file(self):
        reply = QMessageBox.question(self, "New Log File", "Start a New Log File?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.start_new_log_file()

    def start_new_log_file(self):
        """Creates a new log file name and updates the display of the file name.
        """
        date_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        self.log_file_name = f'{date_str}.log'
        self.label_log_name.setText(f'Current Log File:\n{self.log_file_name}')   

    def ask_reset_pid(self):
        reply = QMessageBox.question(self, "Reset PID", "Restore Initial PID State?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.reset_pid()

    def reset_pid(self):
        self.slider_kp.value = self.kp_init
        self.slider_ki.value = self.ki_init
        self.slider_kd.value = self.kd_init
        self.controller.reset_pid()

    def plot_list(self, val_list):
        """Returns a list that contains the elements to plot for the current moment
        in time.
        'val_list':  is the ring buffer that values are drawn from.
        self.log_ix indicates the index of the last element to plot.
        """
        return val_list[self.log_ix + 1:] + val_list[:self.log_ix]

    def handle_control_results(self, vals):

        try: 
            self.delta_t     # will error if this is the first pass

            self.timestamp[self.log_ix] =  vals['timestamp']
            self.delta_t[self.log_ix] = vals['delta_t']
            self.pwm[self.log_ix] = vals['pwm']
            
            self.inner_average[self.log_ix] = vals['inner']['average']
            self.outer_average[self.log_ix] = vals['outer']['average']
            self.info_average[self.log_ix] = vals['info']['average']

            now_ts = time.time()
            ts = list((self.timestamp - now_ts) / 60.0)

            plot_ts = self.plot_list(ts)
            plot_delta_t = self.plot_list(self.delta_t)
            plot_pwm = self.plot_list(self.pwm)

            if max(plot_delta_t) < 2.5 and min(plot_delta_t) > -2.5:
                self.plotDelta.setYRange(-2.5, 2.5)
            else:
                self.plotDelta.enableAutoRange()

            self.delta_t_line.setData(plot_ts, plot_delta_t)
            self.pwm_line.setData(plot_ts, plot_pwm)

            # Needed to update widgets to keep the plot refreshing.
            pg.QtGui.QApplication.processEvents()

        except:
            self.timestamp = np.array(vals['timestamp'] * np.ones(stng.GRAPH_POINTS))
            self.delta_t = [vals['delta_t']] * stng.GRAPH_POINTS
            self.pwm = [vals['pwm']] * stng.GRAPH_POINTS

            self.inner_average = [vals['inner']['average']] * stng.GRAPH_POINTS
            self.outer_average = [vals['outer']['average']] * stng.GRAPH_POINTS
            self.info_average = [vals['info']['average']] * stng.GRAPH_POINTS


            self.delta_t_line = self.plotDelta.plot([], [], pen=pg.mkPen(color=(0, 0, 255), width=3))
            self.pwm_line = self.plotPWM.plot([], [], pen=pg.mkPen(color=(255, 0, 0), width=3))

        finally:
            self.log_ix = (self.log_ix + 1) % stng.GRAPH_POINTS

        print(f"Delta-T: {vals['delta_t']:.2f} F, PWM: {vals['pwm']:.3f}")


def main():

    app = QApplication(sys.argv)
    main = MainWindow()
    main.move(0, 40)
    main.show()

    try:
        sys.exit(app.exec_())

    finally:
        # make sure Heater is turned off
        main.controller.turn_off_pwm()

if __name__=='__main__':
    main()
