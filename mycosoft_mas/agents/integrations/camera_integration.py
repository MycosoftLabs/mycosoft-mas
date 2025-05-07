import os
import cv2
import numpy as np
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CameraIntegration:
    """Handles camera integration for security and visual tasks"""
    
    def __init__(self, config=None):
        self.config = config or self._load_default_config()
        self.camera = None
        self.is_recording = False
        self.recording_writer = None
        self.motion_detector = None
        self.face_detector = None
        self._init_detectors()
    
    def _load_default_config(self):
        """Load default configuration"""
        return {
            "camera_id": int(os.getenv("CAMERA_ID", "0")),
            "resolution": (int(os.getenv("CAMERA_WIDTH", "1280")), 
                          int(os.getenv("CAMERA_HEIGHT", "720"))),
            "fps": int(os.getenv("CAMERA_FPS", "30")),
            "motion_threshold": float(os.getenv("MOTION_THRESHOLD", "0.1")),
            "face_detection_model": os.getenv("FACE_DETECTION_MODEL", "haarcascade_frontalface_default.xml"),
            "recording_path": os.getenv("RECORDING_PATH", "recordings")
        }
    
    def _init_detectors(self):
        """Initialize motion and face detectors"""
        # Create directory for recordings if it doesn't exist
        os.makedirs(self.config["recording_path"], exist_ok=True)
        
        # Initialize face detector
        face_cascade_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "models",
            self.config["face_detection_model"]
        )
        
        # Check if the model file exists, if not, download it
        if not os.path.exists(face_cascade_path):
            os.makedirs(os.path.dirname(face_cascade_path), exist_ok=True)
            # In a real implementation, you would download the model here
            # For now, we'll just use a placeholder
            print(f"Face detection model not found at {face_cascade_path}")
            print("Please download the model manually or implement automatic download")
        
        try:
            self.face_detector = cv2.CascadeClassifier(face_cascade_path)
        except Exception as e:
            print(f"Error initializing face detector: {e}")
            self.face_detector = None
    
    def open_camera(self):
        """Open the camera"""
        if self.camera is not None:
            return True
        
        try:
            self.camera = cv2.VideoCapture(self.config["camera_id"])
            
            # Set resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["resolution"][0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["resolution"][1])
            
            # Set FPS
            self.camera.set(cv2.CAP_PROP_FPS, self.config["fps"])
            
            # Check if camera opened successfully
            if not self.camera.isOpened():
                print("Failed to open camera")
                self.camera = None
                return False
            
            return True
        except Exception as e:
            print(f"Error opening camera: {e}")
            self.camera = None
            return False
    
    def close_camera(self):
        """Close the camera"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        
        if self.is_recording and self.recording_writer is not None:
            self.recording_writer.release()
            self.recording_writer = None
            self.is_recording = False
    
    def capture_frame(self):
        """
        Capture a frame from the camera
        
        Returns:
            Frame as numpy array, or None if failed
        """
        if self.camera is None:
            if not self.open_camera():
                return None
        
        ret, frame = self.camera.read()
        if not ret:
            print("Failed to capture frame")
            return None
        
        return frame
    
    def start_recording(self, filename=None):
        """
        Start recording video
        
        Args:
            filename: Filename to save the recording (default: timestamp)
            
        Returns:
            True if successful, False otherwise
        """
        if self.camera is None:
            if not self.open_camera():
                return False
        
        if self.is_recording:
            return True
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"
        
        # Create full path
        filepath = os.path.join(self.config["recording_path"], filename)
        
        # Get video properties
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.camera.get(cv2.CAP_PROP_FPS))
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.recording_writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
        
        if not self.recording_writer.isOpened():
            print(f"Failed to create video writer for {filepath}")
            self.recording_writer = None
            return False
        
        self.is_recording = True
        return True
    
    def stop_recording(self):
        """
        Stop recording video
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_recording or self.recording_writer is None:
            return True
        
        self.recording_writer.release()
        self.recording_writer = None
        self.is_recording = False
        return True
    
    def detect_motion(self, frame1, frame2):
        """
        Detect motion between two frames
        
        Args:
            frame1: First frame
            frame2: Second frame
            
        Returns:
            True if motion detected, False otherwise
        """
        # Convert frames to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
        
        # Calculate absolute difference
        frame_delta = cv2.absdiff(gray1, gray2)
        
        # Apply threshold
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate to fill in holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check if any contour is large enough
        for contour in contours:
            if cv2.contourArea(contour) > self.config["motion_threshold"] * frame1.shape[0] * frame1.shape[1]:
                return True
        
        return False
    
    def detect_faces(self, frame):
        """
        Detect faces in a frame
        
        Args:
            frame: Frame to detect faces in
            
        Returns:
            List of face rectangles (x, y, w, h)
        """
        if self.face_detector is None:
            return []
        
        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return faces
    
    async def start_motion_detection(self, callback, interval=1.0):
        """
        Start motion detection
        
        Args:
            callback: Callback function to call when motion is detected
            interval: Interval between checks in seconds
            
        Returns:
            Task object
        """
        if self.camera is None:
            if not self.open_camera():
                return None
        
        # Create task
        task = asyncio.create_task(self._motion_detection_loop(callback, interval))
        return task
    
    async def _motion_detection_loop(self, callback, interval):
        """
        Motion detection loop
        
        Args:
            callback: Callback function to call when motion is detected
            interval: Interval between checks in seconds
        """
        # Capture first frame
        frame1 = self.capture_frame()
        if frame1 is None:
            return
        
        while True:
            # Wait for interval
            await asyncio.sleep(interval)
            
            # Capture second frame
            frame2 = self.capture_frame()
            if frame2 is None:
                continue
            
            # Detect motion
            if self.detect_motion(frame1, frame2):
                # Call callback
                await callback(frame2)
            
            # Update first frame
            frame1 = frame2
    
    async def start_face_detection(self, callback, interval=1.0):
        """
        Start face detection
        
        Args:
            callback: Callback function to call when faces are detected
            interval: Interval between checks in seconds
            
        Returns:
            Task object
        """
        if self.camera is None:
            if not self.open_camera():
                return None
        
        # Create task
        task = asyncio.create_task(self._face_detection_loop(callback, interval))
        return task
    
    async def _face_detection_loop(self, callback, interval):
        """
        Face detection loop
        
        Args:
            callback: Callback function to call when faces are detected
            interval: Interval between checks in seconds
        """
        while True:
            # Wait for interval
            await asyncio.sleep(interval)
            
            # Capture frame
            frame = self.capture_frame()
            if frame is None:
                continue
            
            # Detect faces
            faces = self.detect_faces(frame)
            
            # Call callback if faces detected
            if len(faces) > 0:
                await callback(frame, faces)
    
    def save_frame(self, frame, filename=None):
        """
        Save a frame to a file
        
        Args:
            frame: Frame to save
            filename: Filename to save the frame (default: timestamp)
            
        Returns:
            True if successful, False otherwise
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"frame_{timestamp}.jpg"
        
        # Create full path
        filepath = os.path.join(self.config["recording_path"], filename)
        
        # Save frame
        return cv2.imwrite(filepath, frame)
    
    def draw_faces(self, frame, faces):
        """
        Draw rectangles around faces
        
        Args:
            frame: Frame to draw on
            faces: List of face rectangles (x, y, w, h)
            
        Returns:
            Frame with faces drawn
        """
        result = frame.copy()
        
        for (x, y, w, h) in faces:
            cv2.rectangle(result, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        return result 