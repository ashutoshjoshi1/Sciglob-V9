"""
Camera manager for handling camera feed
"""
import cv2
from PyQt5.QtWidgets import QLabel, QGroupBox, QVBoxLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap

class CameraManager:
    def __init__(self, parent):
        """Initialize camera manager"""
        self.parent = parent
        
        # Create camera UI elements
        self.cam_group = QGroupBox("Camera Feed")
        self.cam_group.setObjectName("cameraGroup")
        cam_layout = QVBoxLayout(self.cam_group)
        self.cam_label = QLabel("Camera feed will appear here")
        self.cam_label.setAlignment(Qt.AlignCenter)
        self.cam_label.setMinimumHeight(240)
        self.cam_label.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0; font-size: 12pt; font-weight: bold; border-radius: 5px;")
        cam_layout.addWidget(self.cam_label)
        
        # Initialize camera
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                parent.statusBar().showMessage("Warning: Could not open camera")
                # Try another camera index
                self.camera = cv2.VideoCapture(1)
                if not self.camera.isOpened():
                    parent.statusBar().showMessage("Warning: Could not open any camera")
            else:
                parent.statusBar().showMessage("Camera initialized successfully")
        except Exception as e:
            parent.statusBar().showMessage(f"Camera initialization error: {e}")
            # Create a dummy camera object to prevent errors
            self.camera = None
        
        # Set up camera update timer
        self.camera_timer = QTimer(parent)
        self.camera_timer.timeout.connect(self.update_camera_feed)
        self.camera_timer.start(100)  # Update every 100ms
    
    def update_camera_feed(self):
        """Update camera feed display"""
        if not hasattr(self, 'camera') or self.camera is None or not self.camera.isOpened():
            return
        
        if hasattr(self.parent, '_updating') and self.parent._updating:
            return
        
        self.parent._updating = True
        try:
            ret, frame = self.camera.read()
            if ret:
                # Resize frame to reduce processing time (scale down by 50%)
                frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                
                # Convert frame to RGB format for Qt
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                
                # Convert to QImage and then to QPixmap
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                
                # Scale pixmap to fit the label while maintaining aspect ratio
                self.cam_label.setPixmap(pixmap.scaled(
                    self.cam_label.width(), self.cam_label.height(),
                    Qt.KeepAspectRatio, Qt.FastTransformation
                ))
        except Exception as e:
            print(f"Camera update error: {e}")
        finally:
            self.parent._updating = False
    
    def shutdown(self):
        """Release camera resources"""
        if hasattr(self, 'camera') and self.camera is not None and self.camera.isOpened():
            self.camera.release()



