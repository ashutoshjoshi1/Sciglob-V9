from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QGroupBox, QLabel, QComboBox, QPushButton, QLineEdit, QGridLayout, QHBoxLayout
from serial.tools import list_ports

from drivers.motor import MotorConnectThread, send_move_command

class MotorController(QObject):
    status_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groupbox = QGroupBox("Motor")
        self.groupbox.setObjectName("motorGroup")
        layout = QGridLayout()
        
        # Remove port selection and connect button
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
        
        # Add preset angle dropdown with bold label
        preset_label = QLabel("Preset (°):")
        preset_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(preset_label, 1, 0)
        
        self.angle_preset = QComboBox()
        # Add angles from 0 to 360 in 30 degree increments
        self.angle_preset.addItems([str(i) for i in range(0, 361, 30)])
        self.angle_preset.currentTextChanged.connect(self.preset_selected)
        layout.addWidget(self.angle_preset, 1, 1)
        
        # Keep the custom angle input with bold label
        custom_label = QLabel("Custom (°):")
        custom_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(custom_label, 2, 0)
        
        self.angle_input = QLineEdit()
        self.angle_input.setFixedWidth(60)
        layout.addWidget(self.angle_input, 2, 1)
        
        self.move_btn = QPushButton("Move")
        self.move_btn.setEnabled(False)
        self.move_btn.clicked.connect(self.move)
        layout.addWidget(self.move_btn, 2, 2)

        self.groupbox.setLayout(layout)
        self._connected = False
        self.serial = None

        # If configured port is provided, auto-connect
        if parent is not None and hasattr(parent, 'config'):
            cfg_port = parent.config.get("motor")
            if cfg_port:
                self.port = cfg_port
                self.connect()

    def connect(self):
        """Connect to the motor controller"""
        if not hasattr(self, 'port') or not self.port:
            self.status_signal.emit("No port specified for motor controller")
            return
        
        self.connect_btn.setEnabled(False)
        self.status_signal.emit(f"Connecting to motor controller on {self.port}...")
        
        thread = MotorConnectThread(self.port, parent=self)
        thread.result_signal.connect(self._on_connect)
        thread.start()

    def _on_connect(self, ser, baud, msg):
        self.connect_btn.setEnabled(True)
        self.status_signal.emit(msg)
        if ser:
            self.serial = ser
            self._connected = True
            self.move_btn.setEnabled(True)
            # Move to 0 degrees on successful connection
            self.move_to(0)
        else:
            self._connected = False
            self.move_btn.setEnabled(False)

    def preset_selected(self, angle_text):
        """Handle selection from the preset angle dropdown"""
        self.angle_input.setText(angle_text)
        if self._connected:
            self.move()

    def move(self):
        """Move to the angle specified in the angle input field"""
        try:
            angle = int(self.angle_input.text().strip())
            self.move_to(angle)
        except ValueError:
            self.status_signal.emit("Invalid angle")

    def move_to(self, angle):
        """Move to the specified angle"""
        if not self._connected:
            self.status_signal.emit("Motor not connected")
            return
        
        ok = False
        if self.serial:
            # Convert angle to motor steps (100 steps per degree)
            motor_angle = angle * 100
            ok = send_move_command(self.serial, motor_angle)
            if ok:
                # Update the current angle attribute when move is successful
                self.current_angle_deg = angle
        self.status_signal.emit(f"Moved to {angle}°" if ok else "No ACK")

    def is_connected(self):
        return self._connected







