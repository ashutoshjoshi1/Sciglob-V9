import os
import numpy as np
import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, 
    QWidget, QVBoxLayout as QVBoxLayout2, QLabel, QSpinBox, QCheckBox
)
import pyqtgraph as pg
from pyqtgraph import ViewBox

from drivers.spectrometer import connect_spectrometer, AVS_MeasureCallback, AVS_MeasureCallbackFunc, AVS_GetScopeData, StopMeasureThread, prepare_measurement

class SpectrometerController(QObject):
    status_signal = pyqtSignal(str)

    def __init__(self, parent=None, auto_connect=True):
        super().__init__(parent)
        # Group box UI
        self.groupbox = QGroupBox("Spectrometer")
        self.groupbox.setObjectName("spectrometerGroup")
        main_layout = QVBoxLayout()
        
        # Control buttons with larger font and bold text
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.connect_btn.clicked.connect(self.connect)
        btn_layout.addWidget(self.connect_btn)
        
        self.start_btn = QPushButton("Start")
        self.start_btn.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        btn_layout.addWidget(self.stop_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Add tabs for different plot views
        self.tabs = QTabWidget()
        
        # Pixel plot tab (now first)
        px_tab = QWidget()
        px_layout = QVBoxLayout(px_tab)
        
        # Create pixel plot
        self.plot_px = pg.PlotWidget()
        self.plot_px.setBackground('k')
        self.plot_px.setLabel('left', 'Intensity', units='counts')
        self.plot_px.setLabel('bottom', 'Pixel', units='')
        self.plot_px.showGrid(x=False, y=False)  # No grids
        self.plot_px.setTitle("Spectrum (Pixel)")
        self.plot_px.setXRange(0, 2048)  # Set x-axis range from 0 to 2048
        
        # Create curve for pixel plot
        pen = pg.mkPen(color=(255, 165, 0), width=2)
        self.curve_px = self.plot_px.plot([], [], pen=pen)
        
        px_layout.addWidget(self.plot_px)
        self.tabs.addTab(px_tab, "Pixel")
        
        # Wavelength plot tab (now second)
        wl_tab = QWidget()
        wl_layout = QVBoxLayout(wl_tab)
        
        # Create wavelength plot
        self.plot_wl = pg.PlotWidget()
        self.plot_wl.setBackground('k')
        self.plot_wl.setLabel('left', 'Intensity', units='counts')
        self.plot_wl.setLabel('bottom', 'Wavelength', units='nm')
        self.plot_wl.showGrid(x=False, y=False)  # No grids
        self.plot_wl.setTitle("Spectrum (Wavelength)")
        
        # Create curve for wavelength plot
        pen = pg.mkPen(color=(0, 255, 0), width=2)
        self.curve_wl = self.plot_wl.plot([], [], pen=pen)
        
        wl_layout.addWidget(self.plot_wl)
        self.tabs.addTab(wl_tab, "Wavelength")
        
        # Set the Pixel tab as the default (index 0)
        self.tabs.setCurrentIndex(0)
        
        # Add tabs to main layout
        main_layout.addWidget(self.tabs)
        
        # Add settings panel
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        
        # Integration time
        integ_layout = QHBoxLayout()
        integ_layout.addWidget(QLabel("Integration Time (ms):"))
        self.integ_spinbox = QSpinBox()
        self.integ_spinbox.setRange(1, 10000)
        self.integ_spinbox.setValue(100)
        self.integ_spinbox.setSingleStep(10)
        integ_layout.addWidget(self.integ_spinbox)
        settings_layout.addLayout(integ_layout)
        
        # Cycles
        cycles_layout = QHBoxLayout()
        cycles_layout.addWidget(QLabel("Cycles:"))
        self.cycles_spinbox = QSpinBox()
        self.cycles_spinbox.setRange(1, 100)
        self.cycles_spinbox.setValue(1)
        cycles_layout.addWidget(self.cycles_spinbox)
        settings_layout.addLayout(cycles_layout)
        
        # Repetitions
        rep_layout = QHBoxLayout()
        rep_layout.addWidget(QLabel("Repetitions:"))
        self.repetitions_spinbox = QSpinBox()
        self.repetitions_spinbox.setRange(1, 100)
        self.repetitions_spinbox.setValue(1)
        rep_layout.addWidget(self.repetitions_spinbox)
        settings_layout.addLayout(rep_layout)
        
        # Apply button
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.update_measurement_settings)
        settings_layout.addWidget(self.apply_btn)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # Add the widget attribute
        self.widget = self.groupbox
        
        # Initialize variables
        self.handle = None
        self.wls = []
        self.npix = 0
        self._ready = False
        self.measure_active = False
        self.data = None
        self.cb = None
        self.intens = []  # Initialize intens attribute
        
        # Set the layout
        self.groupbox.setLayout(main_layout)
        
        # Data directory for snapshots
        self.csv_dir = "data"
        os.makedirs(self.csv_dir, exist_ok=True)
        
        # Timer for updating plot
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self._update_plot)
        self.plot_timer.start(200)  # update plot at 5 Hz
        
        # Add downsampling for plots
        self.downsample_factor = 2  # Only plot every 2nd point
        
        # Auto-connect if requested
        if auto_connect:
            # Use QTimer to delay connection attempt slightly to allow UI to initialize
            QTimer.singleShot(500, self.connect)

    def connect(self):
        # Emit status for feedback
        self.status_signal.emit("Connecting to spectrometer...")
        try:
            handle, wavelengths, num_pixels, serial_str = connect_spectrometer()
        except Exception as e:
            self.status_signal.emit(f"Connection failed: {e}")
            return
        self.handle = handle
        # Store wavelength calibration and number of pixels
        self.wls = wavelengths.tolist() if isinstance(wavelengths, np.ndarray) else wavelengths
        self.npix = num_pixels
        self._ready = True
        # Enable measurement start once connected
        self.start_btn.setEnabled(True)
        self.status_signal.emit(f"Spectrometer ready (SN={serial_str})")

    def start(self):
        if not self._ready:
            self.status_signal.emit("Spectrometer not ready")
            return
        
        # Get integration time from UI
        integration_time = float(self.integ_spinbox.value())
        
        # Get cycles and repetitions from UI
        cycles = self.cycles_spinbox.value()
        repetitions = self.repetitions_spinbox.value()
        
        # Calculate averages based on integration time
        # For shorter integration times, use more averages to improve signal quality
        # For longer integration times, use fewer averages to maintain responsiveness
        if integration_time < 10:
            averages = 10  # More averages for very short integration times
        elif integration_time < 100:
            averages = 5   # Medium averages for short integration times
        elif integration_time < 1000:
            averages = 2   # Few averages for medium integration times
        else:
            averages = 1   # No averaging for long integration times
        
        # Store current integration time for data saving
        self.current_integration_time_us = integration_time
        
        # Update status with current settings
        self.status_signal.emit(f"Starting measurement (Int: {integration_time}ms, Avg: {averages}, Cycles: {cycles}, Rep: {repetitions})")
        
        code = prepare_measurement(self.handle, self.npix, 
                                  integration_time_ms=integration_time, 
                                  averages=averages,
                                  cycles=cycles,
                                  repetitions=repetitions)
        if code != 0:
            self.status_signal.emit(f"Prepare error: {code}")
            return
        self.measure_active = True
        self.cb = AVS_MeasureCallbackFunc(self._cb)
        err = AVS_MeasureCallback(self.handle, self.cb, -1)
        if err != 0:
            self.status_signal.emit(f"Callback error: {err}")
            self.measure_active = False
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)  # Enable the apply button when measurement starts
        self.status_signal.emit("Measurement started")

    def _cb(self, p_data, p_user):
        # Spectrometer driver callback (on new scan)
        status_code = p_user[0]
        if status_code == 0:
            _, data = AVS_GetScopeData(self.handle)
            # Ensure intensities list has correct length (up to 2048)
            max_pixels = min(2048, self.npix)
            full = [0.0] * max_pixels
            # Copy only the data we need (up to 2048 pixels)
            data_to_use = data[:max_pixels] if len(data) > max_pixels else data
            full[:len(data_to_use)] = data_to_use
            self.intens = full
            
            # Make sure integration time is accessible to MainWindow
            if hasattr(self, 'current_integration_time_us'):
                # Make it accessible to parent (MainWindow)
                if hasattr(self, 'parent') and self.parent is not None:
                    if not callable(self.parent):  # Check if parent is not a method
                        self.parent.current_integration_time_us = self.current_integration_time_us
            
            # Enable snapshot save and continuous save after first data received
            self.save_btn.setEnabled(True)
            self.toggle_btn.setEnabled(True)
        else:
            self.status_signal.emit(f"Spectrometer error code {status_code}")

    def _update_plot(self):
        """Update the plots with intensity data, ensuring arrays have matching shapes"""
        if not hasattr(self, 'intens') or not self.intens:
            return
        
        try:
            # Get the data arrays
            intensities = np.array(self.intens)
            wavelengths = np.array(self.wls) if self.wls else np.arange(len(intensities))
            
            # Ensure arrays are the same length
            min_length = min(len(intensities), len(wavelengths))
            intensities = intensities[:min_length]
            wavelengths = wavelengths[:min_length]
            
            # Create pixel indices array
            pixel_indices = np.arange(len(intensities))
            
            # Apply downsampling to reduce points plotted
            if hasattr(self, 'downsample_factor') and self.downsample_factor > 1:
                step = self.downsample_factor
                # Use numpy indexing for consistent slicing
                mask = np.zeros(len(intensities), dtype=bool)
                mask[::step] = True
                
                # Apply mask to all arrays
                intensities = intensities[mask]
                wavelengths = wavelengths[mask]
                pixel_indices = pixel_indices[mask]
            
            # Update wavelength plot
            if hasattr(self, 'curve_wl'):
                self.curve_wl.setData(wavelengths, intensities)
            
            # Update pixel plot
            if hasattr(self, 'curve_px'):
                self.curve_px.setData(pixel_indices, intensities)
                
                # Ensure x-axis range stays at 0-2048
                if hasattr(self, 'plot_px'):
                    self.plot_px.setXRange(0, 2048, padding=0)
            
            # Auto-adjust y-axis range based on current data, but not too frequently
            if not hasattr(self, '_range_update_counter'):
                self._range_update_counter = 0
            
            self._range_update_counter += 1
            if self._range_update_counter >= 5:  # Only update range every 5 cycles
                self._range_update_counter = 0
                if len(intensities) > 0 and np.max(intensities) > 0:
                    # Add 10% padding to the top of the y-range
                    max_y = np.max(intensities) * 1.1
                    if hasattr(self, 'plot_px'):
                        self.plot_px.setYRange(0, max_y)
                    if hasattr(self, 'plot_wl'):
                        self.plot_wl.setYRange(0, max_y)
        
        except Exception as e:
            # Log the error but don't crash
            print(f"Plot update error: {e}")
            # Try to recover by clearing the plots
            try:
                if hasattr(self, 'curve_wl'):
                    self.curve_wl.setData([], [])
                if hasattr(self, 'curve_px'):
                    self.curve_px.setData([], [])
            except:
                pass

    def stop(self):
        if not hasattr(self, 'measure_active') or not self.measure_active:
            return
        self.measure_active = False
        th = StopMeasureThread(self.handle, parent=self)
        th.finished_signal.connect(self._on_stop)
        th.start()

    def _on_stop(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)  # Disable the apply button when measurement stops
        self.status_signal.emit("Measurement stopped")

    def save(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.csv_dir, f"snapshot_{ts}.csv")
        try:
            with open(path, 'w') as f:
                f.write("Wavelength (nm),Intensity\n")
                for wl, inten in zip(self.wls, self.intens):
                    if inten != 0:
                        f.write(f"{wl:.4f},{inten:.4f}\n")
            self.status_signal.emit(f"Saved snapshot to {path}")
        except Exception as e:
            self.status_signal.emit(f"Save error: {e}")

    def toggle(self):
        # This method is overridden by MainWindow if parent is provided.
        self.status_signal.emit("Continuous-save not yet implemented")

    def is_ready(self):
        return self._ready

    def update_measurement_settings(self):
        """Update measurement settings without stopping the current measurement"""
        if not self._ready:
            self.status_signal.emit("Spectrometer not ready")
            return
        
        # Get all settings from UI
        integration_time = float(self.integ_spinbox.value())
        cycles = self.cycles_spinbox.value()
        repetitions = self.repetitions_spinbox.value()
        
        # Calculate averages based on integration time
        if integration_time < 10:
            averages = 10
        elif integration_time < 100:
            averages = 5
        elif integration_time < 1000:
            averages = 2
        else:
            averages = 1
        
        # Store current integration time for data saving
        self.current_integration_time_us = integration_time 
        
        if hasattr(self, 'measure_active') and self.measure_active:
            # First stop the current measurement
            self.status_signal.emit(f"Stopping measurement to update settings...")
            self.measure_active = False
            
            # Use StopMeasureThread to properly stop the measurement
            th = StopMeasureThread(self.handle, parent=self)
            th.finished_signal.connect(lambda: self._apply_new_settings(integration_time, averages, cycles, repetitions))
            th.start()
        else:
            # Just prepare the measurement with new settings
            code = prepare_measurement(self.handle, self.npix, 
                                      integration_time_ms=integration_time, 
                                      averages=averages,
                                      cycles=cycles,
                                      repetitions=repetitions)
            if code != 0:
                self.status_signal.emit(f"Settings update error: {code}")
                return
            self.status_signal.emit(f"Settings updated (Int: {integration_time}ms, Avg: {averages}, Cycles: {cycles}, Rep: {repetitions})")

    def _apply_new_settings(self, integration_time, averages, cycles, repetitions):
        """Helper to apply new settings after measurement has stopped"""
        code = prepare_measurement(self.handle, self.npix, 
                                  integration_time_ms=integration_time, 
                                  averages=averages,
                                  cycles=cycles,
                                  repetitions=repetitions)
        if code != 0:
            self.status_signal.emit(f"Settings update error: {code}")
            return
        
        self.cb = AVS_MeasureCallbackFunc(self._cb)
        err = AVS_MeasureCallback(self.handle, self.cb, -1)
        if err != 0:
            self.status_signal.emit(f"Callback error on restart: {err}")
            self.measure_active = False
            return
        
        self.measure_active = True
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(f"Settings updated (Int: {integration_time}ms, Avg: {averages}, Cycles: {cycles}, Rep: {repetitions})")

    # Removed auto_adjust_integration_time method
    # def auto_adjust_integration_time(self):
    #     """Automatically adjust integration time based on peak value and filter wheel position"""
    #     ...



















