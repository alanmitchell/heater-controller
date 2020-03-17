"""A sample of the main settings file for the main.py control program.
Copy this file to user/settings.py and then modify there as appropriate.
"""

# List of Inner Chamber Temperature sensors.  Format for each
# tuple is:
# (Sensor Label, Labjack Analog channel number, thermistor type from heatercontrol.thermistor.py file)
# Sensor Labels must be Unique within this temperature group.
INNER_TEMPS = (
    ('Upper Left Inlet', 8, 'Sure 10K'),
)

# List of Outer Chamber Temperature sensors.  Same format as INNER_TEMPS
# Sensor Labels must be Unique within this temperature group.
OUTER_TEMPS = (
    ('Top', 9, 'Sure 10K'),
)

# List of Informational Temperature sensors.
# Sensor Labels must be Unique within this temperature group.
INFO_TEMPS = (

)

# Divider resistor value used in Thermistor circuits
THERMISTOR_DIVIDER_R = 20000.0

# Analog Channel that reads the voltage that is applied to the
# thermistor circuits on the Labjack
THERMISTOR_APPLIED_V_CH = 15

# Amount of time between updating the PWM heater output
CONTROL_PERIOD = 0.3      # seconds

# PWM Digital Output channel number on Labjack
PWM_CHANNEL = 6

# Total Period of the PWM signal in seconds
PWM_PERIOD = 1.0   # seconds

# Initial PWM max level setting
INIT_PWM_MAX = 1.0

# Range and starting value of PID parameters.
# Format is (min value, starting value, max value)
PID_P = (0.1, 0.3, 0.7)         # use 0.5, 1.5, 4.0 for test chamber
PID_I = (0.0, 0.03, 0.07)       # use 0.02 for test chamber
PID_D = (0.0, 0.0, 2.0)

# Time spacing between plot points in seconds
PLOT_TIME_INTERVAL = 0.5       # seconds

# Total number of points to show on the graphs.
GRAPH_POINTS = 120

# Interval between log points, mesured in plot points, i.e.
# a value of 4 means log every 4th plot point.
LOG_INTERVAL = 6
