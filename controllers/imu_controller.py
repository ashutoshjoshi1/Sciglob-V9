import serial, cv2
from serial.tools import list_ports
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from drivers.imu import start_imu_read_thread
import utils

class IMUController(QObject):
    status_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groupbox = QGroupBox("IMU")
        self.groupbox.setObjectName("imuGroup")
        
        # Use a vertical layout for more compact display
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)  # Reduce spacing
        
        # Remove port controls
        # Instead, use a status indicator
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Not Connected")
        self.status_label.setStyleSheet("color: #f44336;")  # Red for not connected
        status_layout.addWidget(self.status_label)
        
        # Add connect button that uses the port from config
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect)
        status_layout.addWidget(self.connect_btn)
        
        main_layout.addLayout(status_layout)
        
        # Data label - compact but readable
        self.data_label = QLabel("Not connected")
        self.data_label.setStyleSheet("font-size: 10pt;")
        self.data_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.data_label)
        
        self.groupbox.setLayout(main_layout)
        
        self._connected = False
        self.serial = None
        self.latest = {
            'rpy': (0, 0, 0),
            'latitude': 0,
            'longitude': 0,
            'temperature': 0,
            'pressure': 0
        }
        
        # Auto-select config port if provided
        if parent is not None and hasattr(parent, 'config'):
            cfg_port = parent.config.get("imu")
            if cfg_port:
                self.port = cfg_port
                self.connect()

    def connect(self):
        """Connect to the IMU"""
        if not hasattr(self, 'port') or not self.port:
            self.status_signal.emit("No port specified for IMU")
            return
        
        if self._connected:
            return self.status_signal.emit("Already connected")
        
        try:
            self.serial = serial.Serial(self.port, 115200, timeout=1)  # Default to 115200 baud
        except Exception as e:
            self.status_label.setText("Status: Connection Failed")
            return self.status_signal.emit(f"IMU connection failed: {e}")
        
        self._connected = True
        self.status_label.setText("Status: Connected")
        self.status_label.setStyleSheet("color: #4CAF50;")  # Green for connected
        self.status_signal.emit(f"IMU connected on {self.port}")
        
        self.stop_evt = start_imu_read_thread(self.serial, self.latest)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._refresh)
        self.update_timer.start(100)
        
        return True

    def _update_cam(self):
        if self.cam.isOpened():
            ret, frame = self.cam.read()
            if ret:
                # Resize the frame to fit the larger display area
                frame = cv2.resize(frame, (640, 480))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                img = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
                self.cam_label.setPixmap(QPixmap.fromImage(img).scaled(
                    self.cam_label.width(), self.cam_label.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _refresh(self):
        r, p, y = self.latest['rpy']
        lat = self.latest['latitude']
        lon = self.latest['longitude']
        t = self.latest['temperature']
        pres = self.latest['pressure']
        
        # Format the data with larger text and better formatting
        self.data_label.setText(
            f"<table width='100%' cellspacing='5'>"
            f"<tr><td align='right'><b>Roll:</b></td><td align='left'>{r:.1f}°</td>"
            f"<td align='right'><b>Pitch:</b></td><td align='left'>{p:.1f}°</td>"
            f"<td align='right'><b>Yaw:</b></td><td align='left'>{y:.1f}°</td></tr>"
            f"<tr><td align='right'><b>Temp:</b></td><td align='left'>{t:.1f}°C</td>"
            f"<td align='right'><b>Pressure:</b></td><td align='left'>{pres:.1f}hPa</td></tr>"
            f"<tr><td align='right'><b>Lat:</b></td><td align='left'>{lat:.5f}</td>"
            f"<td align='right'><b>Lon:</b></td><td align='left'>{lon:.5f}</td></tr>"
            f"</table>"
        )

    def is_connected(self):
        return self._connected














