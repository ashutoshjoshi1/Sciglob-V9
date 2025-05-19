"""
Routine manager for handling automated routines
"""
import os
import time
import datetime
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer

class RoutineWorker(QThread):
    """Worker thread for executing routine commands"""
    command_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, commands, parent=None):
        super().__init__(parent)
        self.commands = commands
        self.running = True
    
    def run(self):
        """Execute routine commands"""
        for cmd in self.commands:
            if not self.running:
                break
                
            # Process command
            self.command_signal.emit(cmd)
            self.status_signal.emit(f"Executing: {cmd}")
            
            # Handle wait commands directly in the thread
            if cmd.startswith("wait "):
                try:
                    wait_time = int(cmd.split()[1])
                    time.sleep(wait_time / 1000)  # Convert ms to seconds
                except (IndexError, ValueError):
                    self.status_signal.emit(f"Invalid wait command: {cmd}")
            else:
                # For other commands, wait a bit to ensure they complete
                time.sleep(0.5)
        
        self.finished_signal.emit()
    
    def stop(self):
        """Stop routine execution"""
        self.running = False

class RoutineManager(QObject):
    """Manager for routine execution and control"""
    routine_started_signal = pyqtSignal()
    routine_stopped_signal = pyqtSignal()
    routine_finished_signal = pyqtSignal()
    routine_status_changed = pyqtSignal()  # Add this signal
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.routine_commands = []
        self.current_routine_name = "Unknown"
        self.routine_file_path = None
        self.routine_running = False
        self.worker = None
    
    def load_routine_file(self, file_path):
        """Load a routine file"""
        if not file_path:
            return False
        
        try:
            with open(file_path, 'r') as f:
                self.routine_commands = f.readlines()
            
            # Remove comments and empty lines
            self.routine_commands = [line.strip() for line in self.routine_commands 
                                    if line.strip() and not line.strip().startswith('#')]
            
            if self.routine_commands:
                self.routine_file_path = file_path
                self.current_routine_name = os.path.basename(file_path).replace('.txt', '')
                self.routine_status_changed.emit()  # Add this line
                return True
            else:
                return False
            
        except Exception as e:
            self.parent.statusBar().showMessage(f"Error loading routine: {e}")
            return False
    
    def run_routine(self):
        """Run the loaded routine commands"""
        if not self.routine_commands:
            self.parent.statusBar().showMessage("No routine commands loaded")
            return
        
        if self.routine_running:
            # If already running, stop it
            self.stop_routine()
            return
        
        self.routine_running = True
        self.parent.statusBar().showMessage(f"Running routine: {self.current_routine_name}")
        
        # Create and start worker thread
        self.worker = RoutineWorker(self.routine_commands)
        self.worker.command_signal.connect(self._process_command)
        self.worker.status_signal.connect(self.parent.statusBar().showMessage)
        self.worker.finished_signal.connect(self._routine_finished)
        self.worker.start()
        
        # Emit signal that routine has started
        self.routine_started_signal.emit()
        self.routine_status_changed.emit()  # Add this line
    
    def stop_routine(self):
        """Stop the running routine"""
        if self.worker and self.routine_running:
            self.worker.stop()
            self.parent.statusBar().showMessage("Stopping routine...")
            
            # Emit signal that routine has been stopped
            self.routine_stopped_signal.emit()
            self.routine_status_changed.emit()  # Add this line
    
    def _routine_finished(self):
        """Handle routine completion"""
        self.routine_running = False
        self.parent.statusBar().showMessage(f"Routine '{self.current_routine_name}' completed")
        
        # Emit signal that routine has finished
        self.routine_finished_signal.emit()
        self.routine_status_changed.emit()  # Add this line
    
    def _process_command(self, cmd):
        """Process a routine command"""
        parts = cmd.split()
        if not parts:
            return
        
        # Log command
        if parts[0] == "log":
            message = " ".join(parts[1:])
            self.parent.handle_status_message(message)
        
        # Motor commands
        elif parts[0] == "motor" and len(parts) >= 3:
            if parts[1] == "move" and len(parts) >= 3:
                try:
                    angle = float(parts[2])
                    self.parent.hw.motor_ctrl.move_to_angle(angle)
                except (ValueError, IndexError):
                    self.parent.statusBar().showMessage(f"Invalid motor command: {cmd}")
            elif parts[1] == "home":
                self.parent.hw.motor_ctrl.home()
        
        # Filter wheel commands
        elif parts[0] == "filter" and len(parts) >= 3:
            if parts[1] == "position" and len(parts) >= 3:
                try:
                    position = int(parts[2])
                    self.parent.hw.filter_ctrl.move_to_position(position)
                except (ValueError, IndexError):
                    self.parent.statusBar().showMessage(f"Invalid filter command: {cmd}")
            elif parts[1] == "home":
                self.parent.hw.filter_ctrl.home()
        
        # Spectrometer commands
        elif parts[0] == "spectrometer":
            if len(parts) >= 2:
                if parts[1] == "start":
                    self.parent.hw.spec_ctrl.start()
                elif parts[1] == "stop":
                    self.parent.hw.spec_ctrl.stop()
                elif parts[1] == "save":
                    self.parent.hw.spec_ctrl.save()
                elif parts[1] == "settings" and len(parts) >= 5:
                    try:
                        # Format: spectrometer settings <integration_time_ms> <averages> <cycles>
                        integration_time = int(parts[2])
                        averages = int(parts[3])
                        cycles = int(parts[4])
                        repetitions = int(parts[5]) if len(parts) >= 6 else 1
                        
                        # Update spectrometer settings
                        self.parent.hw.spec_ctrl.update_settings(
                            integration_time=integration_time,
                            averages=averages,
                            cycles=cycles,
                            repetitions=repetitions
                        )
                    except (ValueError, IndexError):
                        self.parent.statusBar().showMessage(f"Invalid spectrometer settings command: {cmd}")
        
        # Temperature controller commands
        elif parts[0] == "temp":
            if len(parts) >= 3:
                if parts[1] == "setpoint":
                    try:
                        setpoint = float(parts[2])
                        self.parent.hw.temp_ctrl.set_temperature(setpoint)
                    except (ValueError, IndexError):
                        self.parent.statusBar().showMessage(f"Invalid temperature command: {cmd}")
                elif parts[1] == "off":
                    self.parent.hw.temp_ctrl.disable()
        
        # Data saving commands
        elif parts[0] == "data":
            if len(parts) >= 2:
                if parts[1] == "start":
                    if not self.parent.data_logger.continuous_saving:
                        self.parent.data_logger.toggle_data_saving()
                elif parts[1] == "stop":
                    if self.parent.data_logger.continuous_saving:
                        self.parent.data_logger.toggle_data_saving()
                elif parts[1] == "snapshot":
                    self.parent._save_single_measurement()
        
        # Camera commands
        elif parts[0] == "camera":
            if len(parts) >= 2:
                if parts[1] == "capture":
                    # Capture a still image from the camera
                    try:
                        filename = parts[2] if len(parts) >= 3 else f"capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        self._capture_camera_image(filename)
                    except Exception as e:
                        self.parent.statusBar().showMessage(f"Camera capture error: {e}")
    
    def _capture_camera_image(self, filename):
        """Capture a still image from the camera"""
        if not hasattr(self.parent, 'camera') or not self.parent.camera.camera.isOpened():
            self.parent.statusBar().showMessage("Camera not available")
            return
            
        # Capture frame
        ret, frame = self.parent.camera.camera.read()
        if not ret:
            self.parent.statusBar().showMessage("Failed to capture image")
            return
            
        # Save image
        try:
            # Create images directory if it doesn't exist
            img_dir = os.path.join(os.path.dirname(__file__), "..", "..", "images")
            os.makedirs(img_dir, exist_ok=True)
            
            # Save image with timestamp
            img_path = os.path.join(img_dir, filename)
            import cv2
            cv2.imwrite(img_path, frame)
            self.parent.statusBar().showMessage(f"Image saved to {img_path}")
        except Exception as e:
            self.parent.statusBar().showMessage(f"Error saving image: {e}")
    
    def create_preset_routine(self, preset_name):
        """Create a preset routine file with default commands"""
        # Create schedules directory if it doesn't exist
        schedules_dir = os.path.join(os.path.dirname(__file__), "..", "..", "schedules")
        os.makedirs(schedules_dir, exist_ok=True)
        
        # Create file path
        file_name = f"schedule_{preset_name.lower().replace(' ', '_')}.txt"
        file_path = os.path.join(schedules_dir, file_name)
        
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
                
                elif preset_name == "Full Scan":
                    f.write("# Full scan routine with all filters\n")
                    f.write("log Starting Full Scan sequence\n")
                    f.write("motor move 0\n")
                    f.write("wait 1000\n")
                    
                    # Loop through all filter positions
                    for pos in range(1, 7):  # Assuming 6 filter positions
                        f.write(f"filter position {pos}\n")
                        f.write("wait 1000\n")
                        f.write("spectrometer start\n")
                        f.write("wait 2000\n")
                        f.write(f"log Saving measurement with filter position {pos}\n")
                        f.write("spectrometer save\n")
                        f.write("wait 1000\n")
                    
                    f.write("log Full Scan sequence completed\n")
                
                elif preset_name == "Temperature Test":
                    f.write("# Temperature test routine\n")
                    f.write("log Starting Temperature Test sequence\n")
                    f.write("temp setpoint 20.0\n")
                    f.write("wait 10000\n")  # Wait for temperature to stabilize
                    f.write("spectrometer start\n")
                    f.write("wait 2000\n")
                    f.write("log Saving measurement at 20°C\n")
                    f.write("spectrometer save\n")
                    f.write("temp setpoint 25.0\n")
                    f.write("wait 10000\n")
                    f.write("spectrometer start\n")
                    f.write("wait 2000\n")
                    f.write("log Saving measurement at 25°C\n")
                    f.write("spectrometer save\n")
                    f.write("temp setpoint 30.0\n")
                    f.write("wait 10000\n")
                    f.write("spectrometer start\n")
                    f.write("wait 2000\n")
                    f.write("log Saving measurement at 30°C\n")
                    f.write("spectrometer save\n")
                    f.write("temp off\n")
                    f.write("log Temperature Test sequence completed\n")
            
            return file_path
                
        except Exception as e:
            self.parent.statusBar().showMessage(f"Error creating preset file: {e}")
            return None






