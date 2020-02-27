#!/usr/bin/env python3

"""The main GUI for the heater controller application.  Uses the
PyQt5 framework for the GUI.
"""
import sys  
import os
import time
from datetime import datetime
from pprint import pprint
import json
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
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

def make_temp_list(setting_temp_list, cat_name):
    """Returns a list with items that can be used to fill a combo box with
    temperature names and keys.  The items in the list are two-tuples: 
    (sensor label, sensor tuple key into current results nested dictionary).
    'setting_temp_list' is a list of thermistors from the main application
    settings file.
    """
    
    if len(setting_temp_list) == 0:
        return []
    
    ret_list = [ (f'{cat_name}: Average', (cat_name.lower(), 'average'))]
    for sensor_label, _, _ in setting_temp_list:
        ret_list.append( (f'{cat_name}: {sensor_label}', (cat_name.lower(), 'detail', sensor_label)) )

    return ret_list

class MainWindow(QWidget):
    """The Main application window.  Uses values from the user.settings
    file to initialize the control system.
    """

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
            None
        )
        # I discovered that I cannot create a pyqtgraph inside of the controller
        # callback function.  It works for awhile and then freezes.  I needed to
        # use a QTimer to add real-time graph points.

        self.plotDelta = SimplePlot('Minute (0 = Now)', 'Inner - Outer (°F)')
        self.plotPWM = SimplePlot('Minute (0 = Now)', 'Heater Output, % of Max')
        self.plotPWM.setYRange(0.0, 1.03, padding=0)
        self.plotTemperature = SimplePlot('Minute (0 = Now)', 'Temperature (°F)')
        self.plotTemperature.addLegend()
        
        # combos to select the two sensors to plot on the bottom graph.
        self.combo_sensor1 = QComboBox()
        lbl_sensor1 = QLabel('Sensor 1:')
        lbl_sensor1.setBuddy(self.combo_sensor1)
        self.combo_sensor2 = QComboBox()
        lbl_sensor2 = QLabel('Sensor 2:')
        lbl_sensor2.setBuddy(self.combo_sensor2)

        # Make a list of all the temperature sensors and their associated dictionary
        # keys to populate the combo boxes with.
        temp_list = make_temp_list(stng.INNER_TEMPS, 'Inner')
        temp_list += make_temp_list(stng.OUTER_TEMPS, 'Outer')
        temp_list += make_temp_list(stng.INFO_TEMPS, 'Info')
        # fill the combos and select the starting temperature values.
        ix = 0
        for lbl, data in temp_list:
            if data == ('inner', 'average'):
                combo1_ix = ix    # default item for sensor 1
            if data == ('outer', 'average'):
                combo2_ix = ix    # default item for sensor 2
            self.combo_sensor1.addItem(lbl, data)
            self.combo_sensor2.addItem(lbl, data)
            ix += 1
        self.combo_sensor1.setCurrentIndex(combo1_ix)
        self.combo_sensor2.setCurrentIndex(combo2_ix)

        sensor_box = QHBoxLayout()
        sensor_box.addWidget(lbl_sensor1)
        sensor_box.addWidget(self.combo_sensor1)
        sensor_box.addSpacing(30)
        sensor_box.addWidget(lbl_sensor2)
        sensor_box.addWidget(self.combo_sensor2)
        sensor_box.addStretch(1)

        graph_layout = QVBoxLayout()
        graph_layout.addWidget(self.plotDelta)
        graph_layout.addWidget(self.plotPWM)
        graph_layout.addLayout(sensor_box)
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

        # the current index into the plotting arrays
        self.plot_ix = 0

        # index to keep track of when to log to file
        self.log_ix = 0

        # Start the controller
        self.controller.start()

        # Start a timer to update plots in this GUI
        self.plot_timer = QTimer()
        self.plot_timer.setInterval(int(stng.PLOT_TIME_INTERVAL * 1000))
        self.plot_timer.timeout.connect(self.handle_control_results)
        self.plot_timer.start()

    def closeEvent(self, event):
        # Turn off heater when this window is closed.
        self.controller.turn_off_pwm()

    def enable_heater_change(self):
        """Responds to heater enable checkbox.
        """
        self.controller.enable_control = self.check_enable_heater.isChecked()

    def enable_on_off_change(self):
        """Responds to checkbox to enable Simple On/Off control instead of
        PID control.
        """
        self.controller.enable_on_off_control = self.check_enable_on_off.isChecked()
        self.controller.reset_pid()

    def pid_tuning_change(self, _):
        """One of the PID tuning sliders changed.
        """
        tunings = (self.slider_kp.value, self.slider_ki.value, self.slider_kd.value)
        self.controller.pid_tunings = tunings

    def heater_max_change(self, _):
        """Responds to a change in the slider controlling the maximum heater
        output.
        """
        self.controller.pwm_max = self.slider_heater_max.value

    def ask_new_log_file(self):
        """Verifies that user really wants to start a new log file.
        """
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

        # Make full path to log file
        self.log_file_path = Path(__file__).parent.resolve() / Path(f'logs/{self.log_file_name}')


    def ask_reset_pid(self):
        """Verifies that user really wants to reset the PID tuning parameters.
        """
        reply = QMessageBox.question(self, "Reset PID", "Restore Initial PID Parameters?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.reset_pid()

    def reset_pid(self):
        """Resest the PID tuninig values to their original values provided by the
        settings file.
        """
        self.slider_kp.value = self.kp_init
        self.slider_ki.value = self.ki_init
        self.slider_kd.value = self.kd_init
        # self.controller.reset_pid()     # This resets integral and causes a big drop in output.

    def plot_list(self, val_list):
        """Returns a list that contains the elements to plot for the current moment
        in time.
        'val_list':  is the ring buffer that values are drawn from.
        self.log_ix indicates the index of the last element to plot.
        """
        return val_list[self.plot_ix + 1:] + val_list[:self.plot_ix + 1]

    def make_plot_data_list(self, first_value):
        """Returns a list with length of the GRAPH_POINTS value from the settings
        file.  'first_value' is used to fill the entire list.
        """
        return [first_value] * stng.GRAPH_POINTS

    def extract_a_sensor(self, key_to_sensor: tuple):
        """Returns a list of sensor values extracted from the control_results
        list.  'key_to_sensor' is a tuple of dictionary keys that leads to the
        sensor value within control_results.  The tuple can have one, two, or three
        items as that is the range of depth in the nested dictionary of control results.
        """
        if len(key_to_sensor) == 3:
            k1, k2, k3 = key_to_sensor
            return [item[k1][k2][k3] for item in self.control_results]

        elif len(key_to_sensor) == 2:
            k1, k2 = key_to_sensor
            return [item[k1][k2] for item in self.control_results]

        elif len(key_to_sensor) == 1:
            k1 = key_to_sensor[0]
            return [item[k1] for item in self.control_results]

        else:
            raise ValueError('Invalid key into Control Results list: {key_to_sensor}')

    def handle_control_results(self):
        """Does all the plotting and logging of the control results
        """

        try:
            vals = self.controller.current_results
        except:
            print('Controller Results not ready yet.')
            return

        # get the keys and labels for the two sensors to plot
        sensor1_key = self.combo_sensor1.currentData()
        sensor1_label = self.combo_sensor1.currentText()
        sensor2_key = self.combo_sensor2.currentData()
        sensor2_label = self.combo_sensor2.currentText()

        try: 
            self.delta_t     # this statement will error if this is the first pass

            # record entire results dictionary into a list.
            self.control_results[self.plot_ix] = vals

            # log to file if it is time.  Entire 'vals' dictionary is written to file,
            # using the repr string of the dictionary.  It can be read in and converted 
            # back to a dictionary with the eval() function.
            if self.log_ix % stng.LOG_INTERVAL == 0:
                with open(self.log_file_path, 'a') as fout:
                    fout.write(repr(vals) + '\n')
            
            self.timestamp[self.plot_ix] =  vals['timestamp']
            self.delta_t[self.plot_ix] = vals['delta_t']
            self.pwm[self.plot_ix] = vals['pwm']
            
            now_ts = time.time()
            ts = list((self.timestamp - now_ts) / 60.0)

            plot_ts = self.plot_list(ts)
            plot_delta_t = self.plot_list(self.delta_t)
            plot_pwm = self.plot_list(self.pwm)

            plot_temp1 = self.plot_list(self.extract_a_sensor(sensor1_key))
            plot_temp2 = self.plot_list(self.extract_a_sensor(sensor2_key))

            if max(plot_delta_t) < 2.5 and min(plot_delta_t) > -2.5:
                self.plotDelta.setYRange(-2.5, 2.5)
            else:
                self.plotDelta.enableAutoRange()
            self.plotPWM.setYRange(0.0, 1.0)

            self.delta_t_line.setData(plot_ts, plot_delta_t)
            self.pwm_line.setData(plot_ts, plot_pwm)
            self.temperature_line1.setData(plot_ts, plot_temp1)
            self.temperature_line2.setData(plot_ts, plot_temp2)

            # Needed to update widgets to keep the plot refreshing.
            pg.QtGui.QApplication.processEvents()

        except Exception as e:
            # print(e)
            self.control_results = self.make_plot_data_list(vals)    # creates array to hold entire results dictionary
            self.timestamp = np.array(self.make_plot_data_list(vals['timestamp']))
            self.delta_t = self.make_plot_data_list(vals['delta_t'])
            self.pwm = self.make_plot_data_list(vals['pwm'])

            self.delta_t_line = self.plotDelta.plot([], [], pen=pg.mkPen(color=(0, 0, 255), width=3))
            self.pwm_line = self.plotPWM.plot([], [], pen=pg.mkPen(color=(255, 0, 0), width=3))
            self.temperature_line1 = self.plotTemperature.plot([], [], 
                                                        name='Sensor 1', 
                                                        pen=pg.mkPen(color=(0, 0, 255), width=2))
            self.temperature_line2 = self.plotTemperature.plot([], [], 
                                                        name='Sensor 2', 
                                                        pen=pg.mkPen(color=(58, 153, 106), width=2))

        finally:
            self.plot_ix = (self.plot_ix + 1) % stng.GRAPH_POINTS
            self.log_ix = (self.log_ix + 1) % stng.LOG_INTERVAL

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
