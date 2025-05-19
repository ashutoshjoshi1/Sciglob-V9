"""
Hardware manager for initializing and managing hardware controllers
"""
import os
from PyQt5.QtWidgets import QGroupBox, QWidget
from PyQt5.QtCore import QTimer

from controllers.motor_controller import MotorController
from controllers.filterwheel_controller import FilterWheelController
from controllers.imu_controller import IMUController
from controllers.spectrometer_controller import SpectrometerController
from controllers.temp_controller import TempController
from controllers.thp_controller import THPController

class HardwareManager:
    def __init__(self, parent, config):
        """Initialize hardware controllers"""
        self.parent = parent
        self.config = config
        
        # Initialize controllers
        self._init_controllers()
        
        # Set up update timer for hardware status
        self.update_timer = QTimer(parent)
        self.update_timer.timeout.connect(self._update_indicators)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def _init_controllers(self):
        """Initialize all hardware controllers"""
        # THP sensor
        thp_port = self.config.get("thp_sensor", "COM8")
        try:
            self.thp_ctrl = THPController(port=thp_port, parent=self.parent)
            self.thp_ctrl.status_signal.connect(self.parent.statusBar().showMessage)
        except Exception as e:
            self.parent.statusBar().showMessage(f"THP sensor initialization failed: {e}")
            # Create a dummy THP controller to prevent errors
            self.thp_ctrl = THPController(port=None, parent=self.parent)
            self.thp_ctrl.status_signal.connect(self.parent.statusBar().showMessage)
        
        # Spectrometer - set auto_connect to True
        self.spec_ctrl = SpectrometerController(parent=self.parent, auto_connect=True)
        self.spec_ctrl.status_signal.connect(self.parent.statusBar().showMessage)
        self.spec_ctrl.status_signal.connect(self.parent.handle_status_message)
        # Add widget attribute to match the expected interface
        if hasattr(self.spec_ctrl, 'groupbox'):
            self.spec_ctrl.widget = self.spec_ctrl.groupbox
        
        # Temperature controller
        temp_port = self.config.get("temp_controller", "COM13")
        self.temp_ctrl = TempController(parent=self.parent)
        self.temp_ctrl.port = temp_port  # Set port from config
        self.temp_ctrl.status_signal.connect(self.parent.statusBar().showMessage)
        self.temp_ctrl.status_signal.connect(self.parent.handle_status_message)
        
        # Motor controller
        motor_port = self.config.get("motor", "COM11")
        self.motor_ctrl = MotorController(parent=self.parent)
        self.motor_ctrl.port = motor_port  # Set port from config
        self.motor_ctrl.status_signal.connect(self.parent.statusBar().showMessage)
        self.motor_ctrl.status_signal.connect(self.parent.handle_status_message)
        # Add widget attribute to match the expected interface
        if hasattr(self.motor_ctrl, 'groupbox'):
            self.motor_ctrl.widget = self.motor_ctrl.groupbox
        
        # Filter wheel controller
        filter_port = self.config.get("filterwheel", "COM12")
        self.filter_ctrl = FilterWheelController(parent=self.parent)
        self.filter_ctrl.port = filter_port  # Set port from config
        self.filter_ctrl.status_signal.connect(self.parent.statusBar().showMessage)
        self.filter_ctrl.status_signal.connect(self.parent.handle_status_message)
        # Add widget attribute to match the expected interface
        if hasattr(self.filter_ctrl, 'groupbox'):
            self.filter_ctrl.widget = self.filter_ctrl.groupbox
        
        # IMU controller
        imu_port = self.config.get("imu", "COM14")
        self.imu_ctrl = IMUController(parent=self.parent)
        self.imu_ctrl.port = imu_port  # Set port from config
        self.imu_ctrl.status_signal.connect(self.parent.statusBar().showMessage)
        self.imu_ctrl.status_signal.connect(self.parent.handle_status_message)
        # Add widget attribute to match the expected interface
        if hasattr(self.imu_ctrl, 'groupbox'):
            self.imu_ctrl.widget = self.imu_ctrl.groupbox
    
    def _update_indicators(self):
        """Update hardware status indicators"""
        # Update groupbox titles with connection status (green if connected, red if not)
        for ctrl, title, ok_fn in [
            (self.motor_ctrl, "Motor", self.motor_ctrl.is_connected),
            (self.filter_ctrl, "Filter Wheel", self.filter_ctrl.is_connected),
            (self.imu_ctrl, "IMU", self.imu_ctrl.is_connected),
            (self.spec_ctrl, "Spectrometer", self.spec_ctrl.is_ready),
            (self.temp_ctrl, "Temperature", lambda: hasattr(self.temp_ctrl, 'tc')),
            (self.thp_ctrl, "THP Sensor", self.thp_ctrl.is_connected)
        ]:
            col = "#4caf50" if ok_fn() else "#f44336"  # Green if connected, red if not
            gb = ctrl.groupbox if hasattr(ctrl, 'groupbox') else ctrl.widget
            gb.setTitle(f"● {title}")
            gb.setStyleSheet(f"""
                QGroupBox#{gb.objectName()}::title {{
                    color: {col};
                }}
            """)
    
    def shutdown(self):
        """Shutdown all hardware controllers"""
        # Add any necessary cleanup for hardware controllers
        pass







