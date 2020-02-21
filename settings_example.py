"""A sample of the main settings file for the main.py control program.
Copy this file to user/settings.py and then modify there as appropriate.
"""

# List of Inner Chamber Temperature sensors.  Format for each
# tuple is:
# (Sensor Label, Labjack Analog channel number, thermistor type from heatercontrol.thermistor.py file)
INNER_TEMPS = (
    ('Upper Left Inlet', 8, 'Sure 10K'),
)

# List of Outer Chamber Temperature sensors.  Same format as INNER_TEMPS
OUTER_TEMPS = (
    ('Top', 9, 'Sure 10K'),
)

# List of Informational Temperature sensors.
INFO_TEMPS = (

)

# Amount of time between updating the PWM heater output
CONTROL_PERIOD = 3.0      # seconds

# PWM Digital Output channel number on Labjack
PWM_CHANNEL = 6

# Total Period of the PWM signal in seconds
PWM_PERIOD = 2.0   # seconds

# Initial PWM max level setting
INIT_PWM_MAX = 0.7

# Range and starting value of PID parameters.
# Format is (min value, starting value, max value)
PID_P = (0.5, 1.5, 4.0)
PID_I = (0.0, 0.02, 0.05)
PID_D = (0.0, 0.0, 2.0)
