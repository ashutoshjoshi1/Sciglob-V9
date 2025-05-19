"""
Data logger for saving spectrometer and sensor data
"""
import os
import datetime
import numpy as np

class DataLogger:
    def __init__(self, parent):
        """Initialize data logger"""
        self.parent = parent
        
        # Initialize log file attributes
        self.log_file = None
        self.csv_file = None
        self.csv_file_path = None
        self.log_file_path = None
        self.continuous_saving = False
        
        # Create log directories if they don't exist
        self.log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        self.csv_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.csv_dir, exist_ok=True)
        
        # Data collection attributes
        self._data_collection = []
        self._hardware_changing = False
        self._last_motor_angle = 0
        self._last_filter_position = 0
        
        # Current routine info
        self.current_routine_name = "Unknown"
        self.current_cycles = 1
        self.current_repetitions = 1
    
    def toggle_data_saving(self):
        """Toggle continuous data saving on/off"""
        if not self.continuous_saving:
            if self.csv_file:
                self.csv_file.close()
            if self.log_file:
                self.log_file.close()
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get current routine name if available
            routine_name = getattr(self.parent, 'current_routine_name', "Unknown")
            
            self.csv_file_path = os.path.join(self.csv_dir, f"Scans_{routine_name}_{ts}.csv")
            self.log_file_path = os.path.join(self.log_dir, f"log_{routine_name}_{ts}.txt")
            try:
                self.csv_file = open(self.csv_file_path, "w", encoding="utf-8", newline="")
                self.log_file = open(self.log_file_path, "w", encoding="utf-8")
            except Exception as e:
                self.parent.statusBar().showMessage(f"Cannot open files: {e}")
                return
            
            # Add metadata header with routine information
            self.csv_file.write(f"# Routine: {routine_name}\n")
            
            # Get cycles and repetitions from spectrometer controller if available
            cycles = 1
            repetitions = 1
            if hasattr(self.parent, 'hw') and hasattr(self.parent.hw.spec_ctrl, 'cycles_spinbox'):
                cycles = self.parent.hw.spec_ctrl.cycles_spinbox.value()
            if hasattr(self.parent, 'hw') and hasattr(self.parent.hw.spec_ctrl, 'repetitions_spinbox'):
                repetitions = self.parent.hw.spec_ctrl.repetitions_spinbox.value()
            
            self.csv_file.write(f"# Cycles: {cycles}\n")
            self.csv_file.write(f"# Repetitions: {repetitions}\n")
            self.csv_file.write(f"# Start Time: {ts}\n")
            self.csv_file.write(f"# ----------------------------------------\n")
            
            # Write CSV headers
            headers = [
                "Timestamp", "RoutineName", "Cycles", "Repetitions", 
                "MotorAngle_deg", "FilterPos",
                "Roll_deg", "Pitch_deg", "Yaw_deg", "AccelX_g", "AccelY_g", "AccelZ_g",
                "MagX_uT", "MagY_uT", "MagZ_uT",
                "Pressure_hPa", "Temperature_C", "TempCtrl_curr", "TempCtrl_set", "TempCtrl_aux",
                "Latitude_deg", "Longitude_deg", "IntegrationTime_us",
                "THP_Temp_C", "THP_Humidity_pct", "THP_Pressure_hPa"
            ]
            
            # Add pixel headers
            spec_ctrl = self.parent.hw.spec_ctrl
            headers += [f"Pixel_{i}" for i in range(len(spec_ctrl.intens))]
            self.csv_file.write(",".join(headers) + "\n")
            self.csv_file.flush()
            os.fsync(self.csv_file.fileno())
            
            # Store routine info for later use
            self.current_routine_name = routine_name
            self.current_cycles = cycles
            self.current_repetitions = repetitions
            
            # Initialize data collection for averaging
            self._data_collection = []
            self._collection_start_time = datetime.datetime.now()
            
            # Initialize hardware state tracking
            self._last_motor_angle = 0
            if hasattr(self.parent.hw.motor_ctrl, "current_angle_deg"):
                self._last_motor_angle = self.parent.hw.motor_ctrl.current_angle_deg
            
            self._last_filter_position = self.parent.hw.filter_ctrl.get_position()
            if self._last_filter_position is None:
                self._last_filter_position = getattr(self.parent.hw.filter_ctrl, "current_position", 0)
            
            # Start timers
            integration_time_ms = getattr(spec_ctrl, 'current_integration_time_us', 100000) / 1000
            self.parent.collection_timer.start(250)  # Collect samples every 250ms
            timer_interval = max(1000, min(5000, int(integration_time_ms)))
            self.parent.save_data_timer.start(timer_interval)
            
            self.continuous_saving = True
            self.parent.statusBar().showMessage(f"Started continuous data saving to {self.csv_file_path}")
        else:
            # Stop data saving
            self.continuous_saving = False
            self.parent.collection_timer.stop()
            self.parent.save_data_timer.stop()
            
            # Flush any remaining data
            if hasattr(self, '_csv_buffer') and self._csv_buffer:
                self.csv_file.write(''.join(self._csv_buffer))
                self.csv_file.flush()
                self._csv_buffer = []
                self._csv_buffer_count = 0
            
            # Close files
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
            if self.log_file:
                self.log_file.close()
                self.log_file = None
            
            self.parent.statusBar().showMessage("Stopped continuous data saving")
    
    def collect_data_sample(self):
        """Collect a data sample for averaging"""
        if not self.continuous_saving:
            return
        
        # Check if hardware state has changed
        current_motor_angle = 0
        if hasattr(self.parent.hw.motor_ctrl, "current_angle_deg"):
            current_motor_angle = self.parent.hw.motor_ctrl.current_angle_deg
        
        current_filter_pos = self.parent.hw.filter_ctrl.get_position