"""
Base window class with core UI setup and styling
"""
import sys
import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QStatusBar, QMessageBox, QHBoxLayout, QGroupBox,
    QApplication, QComboBox, QFileDialog, QSpinBox, QDoubleSpinBox, QLineEdit
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap

class BaseWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini ROBOHyPO")
        
        # Get screen size and set window size proportionally
        screen_rect = QApplication.desktop().availableGeometry()
        screen_width, screen_height = screen_rect.width(), screen_rect.height()
        
        # Set window size to 90% of screen size
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.9)
        self.resize(window_width, window_height)
        
        # Set minimum size proportional to screen size
        min_width = min(1280, int(screen_width * 0.7))
        min_height = min(800, int(screen_height * 0.7))
        self.setMinimumSize(min_width, min_height)
        
        # Add flag to prevent overlapping updates
        self._updating = False
        
        # Set application-wide font with size relative to screen resolution
        app = QApplication.instance()
        font = app.font()
        base_font_size = max(9, min(12, int(screen_height / 100)))
        font.setPointSize(base_font_size)
        app.setFont(font)
        
        # Apply responsive stylesheet
        self._apply_stylesheet(base_font_size)
        
        # Load hardware configuration
        self.config = {}
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "hardware_config.json")
            with open(config_path, 'r') as cfg_file:
                self.config = json.load(cfg_file)
        except Exception as e:
            print(f"Config load error: {e}")
        
        # Set up status bar
        self.setStatusBar(QStatusBar())
    
    def _apply_stylesheet(self, base_font_size):
        """Apply application-wide stylesheet with responsive sizing"""
        # For 1920x1080 resolution, reduce the base font size
        if base_font_size > 10:
            base_font_size = 10
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: #1e1e1e;
                color: #e0e0e0;
            }}
            
            QGroupBox {{ 
                font-weight: bold; 
                font-size: {base_font_size + 1}pt;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                margin-top: 1.5ex;
                padding-top: 1ex;
                background-color: #252525;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                color: #e0e0e0;
                position: relative;
                top: -2px;
            }}
            
            QLabel {{
                font-size: {base_font_size}pt;
                color: #e0e0e0;
            }}
            
            QPushButton {{
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 5px 10px;
                font-size: {base_font_size}pt;
                min-height: 20px;
            }}
            
            QPushButton:hover {{
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
            }}
            
            QPushButton:pressed {{
                background-color: #4a86e8;
                color: white;
            }}
            
            QPushButton:disabled {{
                background-color: #2a2a2a;
                color: #5a5a5a;
                border: 1px solid #333333;
            }}
            
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 3px;
                color: #e0e0e0;
                font-size: {base_font_size}pt;
                min-height: 20px;
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #3a3a3a;
                border-left-style: solid;
            }}
            
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
            }}
            
            QCheckBox::indicator:checked {{
                background-color: #4a86e8;
                border: 1px solid #4a86e8;
            }}
        """)
    
    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
