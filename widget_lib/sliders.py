"""Custom Slider Qt5 widgets.
"""
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QSlider, QLabel)


class SliderWithVal(QWidget):
    """Slider with a label showing the current value.  Allows floating
    point values to be used with the slider.
    """

    # Signal that fires when the Slider value is changed.  Parameter is
    # the new value (float) of the slider.
    valueChanged = pyqtSignal(float)

    def __init__(self, 
        val_range, 
        init_val, 
        dec_places=0,
        step_count=200, 
        *args, **kwargs
        ):
        """Parameters:
        val_range:  Two-tuple of floating point value associated with the minimum slider position
            and the maximum slider position, e.g. (1.5, 3.0).
        init_val:  Initial value (float) of the Slider.
        dec_places:  # of decimal places to display in the value label to the right 
            of the slider
        step_count:  Total # of steps in the slider.  Essentially the resolution of the
            slider.  A high value will cause the change event to fire rapidly when sliding.
        """
        super().__init__(*args, **kwargs)

        self.dec_places = dec_places
        self.step_count = step_count

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(step_count)
        self.slider.setSingleStep(1)
        layout.addWidget(self.slider)        
        
        self.val_label = QLabel('')
        layout.addWidget(self.val_label)
        
        self.setLayout(layout)

        self.slider.valueChanged.connect(self.valuechange)

        self.val_range = val_range
        self.value = init_val

    def valuechange(self):
        """Handles a change in value of the slider.  Sets the value label and
        emits the custom signal.
        """
        val = self.value
        self.val_label.setText(f'{val:.{self.dec_places}f}')
        self.valueChanged.emit(val)

    @property
    def val_range(self):
        """Returns (min val, max val) of the slider, floats.
        """
        return self._val_range
    
    @val_range.setter
    def val_range(self, new_range):
        self._val_range = new_range

    @property
    def value(self):
        """Returns the value of the slider (float).
        """
        min_val, max_val = self._val_range
        return self.slider.value() / self.step_count * (max_val - min_val) + min_val

    @value.setter
    def value(self, new_val):
        min_val, max_val = self._val_range
        if (max_val - min_val) != 0.0:
            # determine integer value to underlying slider to.
            slider_val = round((new_val - min_val) / (max_val -  min_val) * self.step_count)
        else:
            # no range to slider
            slider_val = 0
        self.slider.setValue(slider_val)
