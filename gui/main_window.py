"""
Main window for the Mini ROBOHyPO application
"""
import sys
import os
import datetime
import numpy as np
import cv2

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QStatusBar, QMessageBox, QHBoxLayout, QGroupBox,
    QApplication, QComboBox, QFileDialog, QSpinBox, QDoubleSpinBox, QLineEdit,
    QCheckBox, QTabWidget
)
from PyQt5.QtCore import QTimer, Qt, QDateTime
from PyQt5.QtGui import QImage, QPixmap

from gui.components.base_window import BaseWindow
from gui.components.hardware_manager import HardwareManager
from gui.components.camera_manager import CameraManager
from gui.components.data_logger import DataLogger
from gui.components.routine_manager import RoutineManager

class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize timers
        self.hardware_change_timer = QTimer(self)
        self.collection_timer = QTimer(self)
        self.save_data_timer = QTimer(self)
        
        # Initialize managers
        self.hw = HardwareManager(self, self.config)
        self.camera = CameraManager(self)
        self.data_logger = DataLogger(self)
        self.routine_manager = RoutineManager(self)
        
        # Initialize UI
        self._init_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Show status message
        self.statusBar().showMessage("Application initialized")
        
        # Auto-connect spectrometer is handled in the SpectrometerController initialization
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Create central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Create main horizontal splitter for left and right sections
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Create left section with spectrometer
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Add spectrometer widget to left layout
        left_layout.addWidget(self.hw.spec_ctrl.widget)
        
        # Add left widget to main splitter
        main_splitter.addWidget(left_widget)
        
        # Create right section with camera feed at top and hardware controls below
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Add camera feed at the top
        right_layout.addWidget(self.camera.cam_group)
        
        # Add routine control panel ABOVE hardware controls
        routine_group = QGroupBox("Routine Control")
        routine_group_layout = QVBoxLayout(routine_group)
        
        # Add routine controls
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Select Preset...")
        self.preset_combo.addItems(["Solar Spectrum", "Dark Current", "Calibration", "Full Scan", "Temperature Test"])
        routine_group_layout.addWidget(QLabel("Preset Routines:"))
        routine_group_layout.addWidget(self.preset_combo)
        
        # Add custom routine button
        self.load_routine_btn = QPushButton("Load Custom Routine")
        routine_group_layout.addWidget(self.load_routine_btn)
        
        # Add routine status and control
        self.routine_status = QLabel("No routine loaded")
        routine_group_layout.addWidget(self.routine_status)
        
        self.run_routine_btn = QPushButton("Run Routine")
        self.run_routine_btn.setEnabled(False)
        routine_group_layout.addWidget(self.run_routine_btn)
        
        # Set the layout for the routine group
        routine_group.setLayout(routine_group_layout)
        
        # Add routine group to right layout BEFORE hardware controls
        right_layout.addWidget(routine_group)
        
        # Add hardware controls in a grid layout
        hardware_group = QGroupBox("Hardware Controls")
        hardware_layout = QGridLayout()
        
        # Add hardware controllers to the grid
        # Row 0: Motor and Filter Wheel
        hardware_layout.addWidget(self.hw.motor_ctrl.widget, 0, 0)
        hardware_layout.addWidget(self.hw.filter_ctrl.widget, 0, 1)
        
        # Row 1: IMU and Temperature Controller
        hardware_layout.addWidget(self.hw.imu_ctrl.widget, 1, 0)
        hardware_layout.addWidget(self.hw.temp_ctrl.widget, 1, 1)
        
        # Row 2: THP Sensor
        hardware_layout.addWidget(self.hw.thp_ctrl.widget, 2, 0, 1, 2)
        
        hardware_group.setLayout(hardware_layout)
        right_layout.addWidget(hardware_group)
        
        # Add right widget to main splitter
        main_splitter.addWidget(right_widget)
        
        # Set initial splitter sizes (60% left, 40% right)
        main_splitter.setSizes([600, 400])
    
    def _connect_signals(self):
        """Connect UI signals to slots"""
        # Connect routine controls
        self.preset_combo.currentIndexChanged.connect(self._handle_preset_change)
        self.load_routine_btn.clicked.connect(self._load_custom_routine)
        self.run_routine_btn.clicked.connect(self._toggle_routine)
        
        # Connect routine manager signals
        self.routine_manager.routine_status_changed.connect(self._update_routine_status)
        self.routine_manager.routine_finished_signal.connect(self._routine_finished)
        
        # Connect hardware change timer
        self.hardware_change_timer.timeout.connect(self._resume_after_hardware_change)  # Change this line
    
    def _handle_preset_change(self, index):
        """Handle preset routine selection"""
        if index <= 0:
            self.routine_status.setText("No routine loaded")
            self.run_routine_btn.setEnabled(False)
            return
        
        preset_name = self.preset_combo.currentText()
        preset_file = f"schedule_{preset_name.lower().replace(' ', '_')}.txt"
        preset_path = os.path.join(os.path.dirname(__file__), "..", "schedules", preset_file)
        
        # Create preset file if it doesn't exist
        if not os.path.exists(preset_path):
            self._create_preset_schedule_file(preset_name, preset_path)
        
        # Load the preset file
        try:
            with open(preset_path, 'r') as f:
                self.routine_commands = f.readlines()
            
            # Remove comments and empty lines
            self.routine_commands = [line.strip() for line in self.routine_commands 
                                    if line.strip() and not line.strip().startswith('#')]
            
            if self.routine_commands:
                self.routine_status.setText(f"Loaded: {preset_name}\n{len(self.routine_commands)} commands")
                self.run_routine_btn.setEnabled(True)
                self.routine_file_path = preset_path
                self.current_routine_name = preset_name
            else:
                self.routine_status.setText("No valid commands in preset")
                self.run_routine_btn.setEnabled(False)
                
        except Exception as e:
            self.statusBar().showMessage(f"Error loading preset schedule: {e}")
            self.routine_status.setText(f"Error: {str(e)}")
            self.run_routine_btn.setEnabled(False)
    
    def _create_preset_schedule_file(self, preset_name, file_path):
        """Create a preset schedule file with default commands"""
        try:
            with open(file_path, 'w') as f:
                f.write(f"# {preset_name} Schedule - Created {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                if preset_name == "Solar Spectrum":
                    f.write("# Solar spectrum measurement routine\n")
                    f.write("log Starting Solar Spectrum measurement\n")
                    f.write("motor move 0\n")
                    f.write("wait 1000\n")
                    f.write("filter position 1\n")
                    f.write("wait 1000\n")
                    f.write("spectrometer start\n")
                    f.write("wait 2000\n")
                    f.write("spectrometer save\n")
                    f.write("log Solar Spectrum measurement completed\n")
                
                elif preset_name == "Dark Current":
                    f.write("# Dark current measurement routine\n")
                    f.write("log Starting Dark Current measurement\n")
                    f.write("filter position 6\n")  # Assuming position 6 is dark filter
                    f.write("wait 1000\n")
                    f.write("spectrometer start\n")
                    f.write("wait 2000\n")
                    f.write("spectrometer save\n")
                    f.write("log Dark Current measurement completed\n")
                
                elif preset_name == "Calibration":
                    f.write("# Calibration routine\n")
                    f.write("log Starting Calibration sequence\n")
                    f.write("motor move 0\n")
                    f.write("wait 1000\n")
                    f.write("filter position 1\n")
                    f.write("wait 1000\n")
                    f.write("spectrometer start\n")
                    f.write("wait 2000\n")
                    f.write("spectrometer save\n")
                    f.write("filter position 2\n")
                    f.write("wait 1000\n")
                    f.write("spectrometer start\n")
                    f.write("wait 2000\n")
                    f.write("spectrometer save\n")
                    f.write("log Calibration sequence completed\n")
        except Exception as e:
            self.statusBar().showMessage(f"Error creating preset file: {e}")
    
    def load_routine_file(self):
        """Load a custom routine code file for automated hardware control"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Routine File", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                self.routine_commands = f.readlines()
            
            # Remove comments and empty lines
            self.routine_commands = [line.strip() for line in self.routine_commands 
                                    if line.strip() and not line.strip().startswith('#')]
            
            if self.routine_commands:
                self.routine_status.setText(f"Loaded: {os.path.basename(file_path)}\n{len(self.routine_commands)} commands")
                self.run_routine_btn.setEnabled(True)
                # Reset preset dropdown to avoid confusion
                self.preset_combo.setCurrentIndex(0)
                self.routine_file_path = file_path
                self.current_routine_name = os.path.basename(file_path).replace('.txt', '')
            else:
                self.routine_status.setText("No valid commands in file")
                self.run_routine_btn.setEnabled(False)
                
        except Exception as e:
            self.statusBar().showMessage(f"Error loading routine: {e}")
            self.routine_status.setText(f"Error: {str(e)}")
            self.run_routine_btn.setEnabled(False)
    
    def run_routine(self):
        """Run the loaded routine commands"""
        if not self.routine_commands or self.routine_running:
            return
        
        self.routine_running = True
        self.run_routine_btn.setText("Stop Routine")
        self.statusBar().showMessage(f"Running routine: {self.current_routine_name}")
        
        # Start routine execution in a separate thread or timer
        # Implementation depends on how you want to handle command execution
        
        # For now, just a placeholder
        self.statusBar().showMessage("Routine execution not implemented yet")
        self.routine_running = False
        self.run_routine_btn.setText("Run Routine")
    
    def toggle_data_saving(self):
        """Toggle continuous data saving on/off"""
        self._toggle_continuous_saving()
    
    def _save_single_measurement(self):
        """Save a single measurement"""
        # Implementation depends on how you want to handle single measurements
        self.statusBar().showMessage("Single measurement save not implemented yet")
    
    def _resume_after_hardware_change(self):
        """Resume data collection after hardware change"""
        self.data_logger._hardware_changing = False
        self.statusBar().showMessage("Resuming data collection")
    
    def handle_status_message(self, message):
        """Handle status messages from hardware controllers"""
        # Log the message if data logging is active
        if self.data_logger.log_file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.data_logger.log_file.write(f"{timestamp} [INFO] {message}\n")
            self.data_logger.log_file.flush()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Release camera resources
        self.camera.shutdown()
        
        # Shutdown hardware controllers
        self.hw.shutdown()
        
        # Close data files
        if self.data_logger.continuous_saving:
            self.data_logger.toggle_data_saving()
        
        # Call the parent class closeEvent
        super().closeEvent(event)

    def _toggle_continuous_saving(self):
        """Toggle continuous data saving"""
        if not self.data_logger.continuous_saving:
            self.data_logger.toggle_data_saving()
            self.continuous_save_btn.setText("Stop Continuous Saving")
        else:
            self.data_logger.toggle_data_saving()
            self.continuous_save_btn.setText("Start Continuous Saving")

    def _load_custom_routine(self):
        """Load a custom routine file"""
        self.load_routine_file()

    def _toggle_routine(self):
        """Toggle routine execution on/off"""
        if not hasattr(self, 'routine_running'):
            self.routine_running = False
        
        if not self.routine_running:
            self.run_routine()
            self.run_routine_btn.setText("Stop Routine")
            self.routine_running = True
        else:
            # Stop the routine
            self.routine_running = False
            self.run_routine_btn.setText("Run Routine")
            self.statusBar().showMessage("Routine stopped")

    def _update_routine_status(self):
        """Update routine status display"""
        if hasattr(self.routine_manager, 'routine_running') and self.routine_manager.routine_running:
            self.routine_status.setText(f"Running: {self.routine_manager.current_routine_name}")
            self.run_routine_btn.setText("Stop Routine")
        else:
            self.routine_status.setText(f"Loaded: {self.routine_manager.current_routine_name}")
            self.run_routine_btn.setText("Run Routine")

    def _routine_finished(self):
        """Handle routine completion"""
        self.routine_running = False
        self.run_routine_btn.setText("Run Routine")
        self.routine_status.setText(f"Completed: {self.routine_manager.current_routine_name}")














