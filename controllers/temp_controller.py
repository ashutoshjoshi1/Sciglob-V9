from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QGroupBox, QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox, QDoubleSpinBox, QHBoxLayout
from serial.tools import list_ports

from drivers.tc36_25_driver import TC36_25

class TempController(QObject):
    status_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Group box for Temperature Controller
        self.groupbox = QGroupBox("Temperature Controller")
        self.groupbox.setObjectName("tempGroup")
        # Add widget attribute to match the expected interface
        self.widget = self.groupbox
        
        layout = QGridLayout()
        layout.setVerticalSpacing(8)  # Increase vertical spacing between rows
        
        # Remove port selection
        # Instead, use a status indicator
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Not Connected")
        self.status_label.setStyleSheet("color: #f44336;")  # Red for not connected
        status_layout.addWidget(self.status_label)
        
        # Add connect button that uses the port from config
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect)
        status_layout.addWidget(self.connect_btn)
        
        layout.addLayout(status_layout, 0, 0, 1, 3)
        
        # Current temperature with bold label and larger font
        temp_label = QLabel("Current:")
        temp_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(temp_label, 1, 0)
        
        self.temp_display = QLabel("-- °C")
        self.temp_display.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(self.temp_display, 1, 1)
        
        # Add auxiliary temperature display
        aux_temp_label = QLabel("Auxiliary:")
        aux_temp_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(aux_temp_label, 2, 0)
        
        self.aux_temp_display = QLabel("-- °C")
        self.aux_temp_display.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(self.aux_temp_display, 2, 1)
        
        # Setpoint with bold label and more intuitive layout
        setpoint_label = QLabel("Set Temperature:")
        setpoint_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(setpoint_label, 3, 0)
        
        # Use a horizontal layout for the setpoint controls
        setpoint_layout = QHBoxLayout()
        setpoint_layout.setContentsMargins(0, 5, 0, 0)  # Add some top margin
        
        self.setpoint_spin = QDoubleSpinBox()
        self.setpoint_spin.setRange(15, 40)
        self.setpoint_spin.setValue(20.0)
        self.setpoint_spin.setSingleStep(0.5)
        self.setpoint_spin.setSuffix(" °C")
        self.setpoint_spin.setEnabled(False)
        self.setpoint_spin.setStyleSheet("font-size: 11pt;")
        self.setpoint_spin.setMinimumWidth(100)
        setpoint_layout.addWidget(self.setpoint_spin)
        
        self.set_btn = QPushButton("Set")
        self.set_btn.setEnabled(False)
        self.set_btn.clicked.connect(self.set_temp)
        self.set_btn.setStyleSheet("font-weight: bold; font-size: 11pt;")
        setpoint_layout.addWidget(self.set_btn)
        
        layout.addLayout(setpoint_layout, 3, 1, 1, 2)
        
        self.groupbox.setLayout(layout)

        # Auto-select config port if provided
        if parent is not None and hasattr(parent, 'config'):
            cfg_port = parent.config.get("temp_controller")
            if cfg_port:
                self.port = cfg_port
                self.connect()

    def set_preset_temp(self, temp):
        """Set temperature to a preset value (kept for backward compatibility)"""
        if not hasattr(self, 'tc'):
            self.status_signal.emit("Temperature controller not connected")
            return
        
        self.setpoint_spin.setValue(temp)
        self.set_temp()

    def set_temp(self):
        """Set the temperature setpoint"""
        try:
            t = self.setpoint_spin.value()
            self.tc.set_setpoint(t)
            self.status_signal.emit(f"Temperature setpoint set to {t:.1f}°C")
        except Exception as e:
            self.status_signal.emit(f"Failed to set temperature: {e}")

    def _upd(self):
        """Update the current temperature display with timeout protection"""
        try:
            # Set a timeout for temperature reading
            if not hasattr(self, '_temp_read_timer') or self._temp_read_timer is None:
                from threading import Timer
                self._temp_read_timer = Timer(0.5, self._timeout_temp_read)
                self._temp_read_timer.daemon = True
                self._temp_read_timer.start()
                
            # Read primary temperature
            current = self.tc.get_temperature()
            
            # Read auxiliary temperature
            try:
                aux_temp = self.tc.get_auxiliary_temperature()
                self.aux_temp_display.setText(f"{aux_temp:.2f} °C")
                # Store auxiliary temperature for data logging
                self._aux_temperature = aux_temp
            except Exception as e:
                self.aux_temp_display.setText("-- °C")
                self._aux_temperature = 0.0
                # Only log error if it's not a timeout
                if not hasattr(self, '_temp_read_timeout') or not self._temp_read_timeout:
                    self.status_signal.emit(f"Auxiliary temperature read error: {e}")
            
            # Cancel timeout timer if successful
            if hasattr(self, '_temp_read_timer') and self._temp_read_timer is not None:
                try:
                    if self._temp_read_timer.is_alive():
                        self._temp_read_timer.cancel()
                except Exception:
                    # If there's any issue with the timer, just create a new one next time
                    pass
                self._temp_read_timer = None
            
            self.temp_display.setText(f"{current:.2f} °C")
            
            # Reset timeout flag if successful
            if hasattr(self, '_temp_read_timeout'):
                self._temp_read_timeout = False
            
        except Exception as e:
            self.temp_display.setText("-- °C")
            self.aux_temp_display.setText("-- °C")
            # Only show error message if it's not a timeout
            if not hasattr(self, '_temp_read_timeout') or not self._temp_read_timeout:
                self.status_signal.emit(f"Temperature read error: {e}")

    def _timeout_temp_read(self):
        """Called when temperature reading times out"""
        self._temp_read_timeout = True
        self.temp_display.setText("-- °C")
        self.status_signal.emit("Temperature read timed out")
        self._temp_read_timer = None

    @property
    def current_temp(self):
        # Current temperature reading from controller
        try:
            text = self.temp_display.text()
            return float(text.split()[0])
        except:
            return 0.0

    @property
    def setpoint(self):
        # Last set temperature (if known)
        try:
            return self.setpoint_spin.value()
        except:
            return 0.0

    @property
    def auxiliary_temp(self):
        # Auxiliary temperature reading from controller
        try:
            if hasattr(self, '_aux_temperature'):
                return self._aux_temperature
            return 0.0
        except:
            return 0.0

    def is_connected(self):
        """Check if temperature controller is connected"""
        return hasattr(self, 'tc')

    def connect(self):
        """Connect to the temperature controller"""
        if not hasattr(self, 'port') or not self.port:
            self.status_signal.emit("No port specified for temperature controller")
            return
        
        self.status_signal.emit(f"Connecting to temperature controller on {self.port}...")
        
        try:
            self.tc = TC36_25(self.port)
            # Once connected, enable computer control and turn on power
            self.tc.enable_computer_setpoint()
            self.tc.power(True)
            
            # Enable the setpoint control
            self.setpoint_spin.setEnabled(True)
            self.set_btn.setEnabled(True)
            
            # Update status indicator
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: #4CAF50;")  # Green for connected
            
            # Start periodic update
            if not hasattr(self, 'timer') or not self.timer.isActive():
                self.timer = QTimer(self)
                self.timer.timeout.connect(self._upd)
                self.timer.start(1000)
            
            self.status_signal.emit(f"Temperature controller connected on {self.port}")
            return True
        except Exception as e:
            self.status_label.setText("Status: Connection Failed")
            self.status_signal.emit(f"Temperature controller connection failed: {e}")
            return False

    def set_temperature(self, temp):
        """Set temperature to a specific value (for routine manager)"""
        if not hasattr(self, 'tc'):
            self.status_signal.emit("Temperature controller not connected")
            return False
        
        try:
            self.setpoint_spin.setValue(temp)
            self.set_temp()
            return True
        except Exception as e:
            self.status_signal.emit(f"Failed to set temperature: {e}")
            return False

    def disable(self):
        """Turn off the temperature controller"""
        if not hasattr(self, 'tc'):
            self.status_signal.emit("Temperature controller not connected")
            return False
        
        try:
            self.tc.power(False)
            self.status_signal.emit("Temperature controller turned off")
            return True
        except Exception as e:
            self.status_signal.emit(f"Failed to turn off temperature controller: {e}")
            return False
