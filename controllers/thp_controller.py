from PyQt5.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt5.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from drivers.thp_sensor import read_thp_sensor_data

class THPController(QObject):
    status_signal = pyqtSignal(str)

    def __init__(self, port=None, parent=None):
        super().__init__(parent)
        self.port = port
        self.groupbox = QGroupBox("THP Sensor")
        self.groupbox.setObjectName("thpGroup")
        # Add widget attribute to match the expected interface
        self.widget = self.groupbox
        
        layout = QVBoxLayout()
        
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
        
        layout.addLayout(status_layout)
        
        # Readings display
        self.readings_label = QLabel("Sensor not connected")
        layout.addWidget(self.readings_label)
        
        # Reconnect button
        self.reconnect_btn = QPushButton("Reconnect")
        self.reconnect_btn.clicked.connect(self.reconnect)
        layout.addWidget(self.reconnect_btn)
        
        self.groupbox.setLayout(layout)
        
        # Initialize latest data
        self.latest = {
            "temperature": 0.0,
            "humidity": 0.0,
            "pressure": 0.0,
            "sensor_id": ""
        }
        
        # Start update timer if port is provided
        if port is not None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._update_data)
            self.timer.start(2000)  # Update every 2 seconds
        else:
            self.status_signal.emit("THP sensor not configured - set COM port in config")

        # Auto-select config port if provided
        if parent is not None and hasattr(parent, 'config'):
            cfg_port = parent.config.get("thp_sensor")
            if cfg_port:
                self.port = cfg_port
                self.connect()

    def _update_data(self):
        try:
            data = read_thp_sensor_data(self.port)
            if data:
                self.latest = data
                self.readings_label.setText(
                    f"Temp: {data['temperature']:.1f} °C | "
                    f"Humidity: {data['humidity']:.1f} % | "
                    f"Pressure: {data['pressure']:.1f} hPa"
                )
            else:
                # Update the label to show connection issue
                self.readings_label.setText("Sensor not connected - check COM port")
                self.status_signal.emit(f"THP sensor read failed on port {self.port}")
        except Exception as e:
            self.readings_label.setText("Sensor error - check connection")
            self.status_signal.emit(f"THP sensor error: {e}")

    def get_latest(self):
        return self.latest

    def is_connected(self):
        """Check if the THP sensor is connected"""
        if not hasattr(self, 'latest'):
            return False
        return self.latest.get("temperature", 0.0) != 0.0

    def reconnect(self):
        """Try to reconnect to the THP sensor"""
        self.status_signal.emit(f"Attempting to reconnect THP sensor on {self.port}")
        data = read_thp_sensor_data(self.port)
        if data:
            self.latest = data
            self.readings_label.setText(
                f"Temp: {data['temperature']:.1f} °C | "
                f"Humidity: {data['humidity']:.1f} % | "
                f"Pressure: {data['pressure']:.1f} hPa"
            )
            self.status_signal.emit("THP sensor reconnected successfully")
            return True
        else:
            self.readings_label.setText("Reconnect failed - check COM port")
            self.status_signal.emit(f"THP sensor reconnect failed on port {self.port}")
            return False

    def connect(self):
        """Connect to the THP sensor"""
        if not self.port:
            self.status_signal.emit("No port specified for THP sensor")
            return False
        
        self.status_signal.emit(f"Connecting to THP sensor on {self.port}...")
        
        try:
            # Attempt to read data to verify connection
            data = read_thp_sensor_data(self.port)
            if data:
                self.latest = data
                self.readings_label.setText(
                    f"Temp: {data['temperature']:.1f} °C | "
                    f"Humidity: {data['humidity']:.1f} % | "
                    f"Pressure: {data['pressure']:.1f} hPa"
                )
                self.status_label.setText("Status: Connected")
                self.status_label.setStyleSheet("color: #4CAF50;")  # Green for connected
                self.status_signal.emit(f"THP sensor connected on {self.port}")
                
                # Start update timer if not already running
                if not hasattr(self, 'timer') or not self.timer.isActive():
                    self.timer = QTimer(self)
                    self.timer.timeout.connect(self._update_data)
                    self.timer.start(2000)  # Update every 2 seconds
                
                return True
            else:
                self.status_label.setText("Status: Connection Failed")
                self.status_signal.emit(f"THP sensor connection failed on {self.port}")
                return False
        except Exception as e:
            self.status_label.setText("Status: Error")
            self.status_signal.emit(f"THP sensor connection error: {e}")
            return False







