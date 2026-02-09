"""
SeeWhozThere Hailo AI Processor Module

This module implements face detection using the Raspberry Pi AI HAT+ (Hailo-8).
It processes RTSP camera streams in real-time and records visitor sightings.

Hardware Requirements:
- Raspberry Pi 5
- Raspberry Pi AI HAT+ (Hailo-8L 13 TOPS or Hailo-8 26 TOPS)
- IP camera with RTSP support (e.g., Tapo C310)

Performance:
- Face detection: 300-400 FPS (with Hailo-8L)
- Multiple camera support
- Real-time processing with minimal latency
"""

import os
import cv2
import time
import subprocess
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import pytz
import threading
import queue

from app.config import CAMERAS, TIMEZONE
from app.database import get_db
from app.hailo_face_detector_v4 import create_face_detector


class HailoProcessor:
    """
    Real-time face detection processor using Hailo AI HAT+.
    
    This processor:
    1. Connects to RTSP camera streams
    2. Detects faces using Hailo AI accelerator
    3. Tracks and identifies visitors
    4. Records sightings in the database
    """
    
    def __init__(self):
        """Initialize the Hailo processor"""
        self.db = get_db()
        self.running = False
        self.camera_threads = {}
        self.frame_queues = {}
        self.hailo_available = self._check_hailo_device()
        
        # Face detection parameters
        self.detection_interval = 1.0  # Process every N seconds per camera
        self.confidence_threshold = 0.6
        self.min_face_size = (50, 50)  # Minimum face dimensions in pixels
        
        # Snapshot storage
        self.snapshot_dir = "data/snapshots"
        os.makedirs(self.snapshot_dir, exist_ok=True)
        
        # Initialize face detector with Hailo support
        model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'retinaface_mobilenet_v1.hef')
        self.face_detector = create_face_detector(
            model_path=model_path,
            confidence_threshold=self.confidence_threshold,
            use_hailo=self.hailo_available
        )
        
        # Start the face detector pipeline
        self.face_detector.start()
        
        print(f"[HailoProcessor] Initialized")
        print(f"[HailoProcessor] Hailo device available: {self.hailo_available}")
        print(f"[HailoProcessor] Face detector: {type(self.face_detector).__name__}")
    
    def _check_hailo_device(self) -> bool:
        """
        Check if Hailo AI HAT+ is available and functioning.
        
        Returns:
            True if Hailo device is detected, False otherwise
        """
        try:
            # Check for /dev/hailo0
            if os.path.exists("/dev/hailo0"):
                print("[HailoProcessor] Found /dev/hailo0")
                
                # Try to run hailortcli scan
                result = subprocess.run(
                    ["hailortcli", "scan"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and "Device:" in result.stdout:
                    print("[HailoProcessor] Hailo device verified via hailortcli")
                    return True
                else:
                    print("[HailoProcessor] hailortcli scan failed")
                    return False
            else:
                print("[HailoProcessor] /dev/hailo0 not found")
                return False
                
        except FileNotFoundError:
            print("[HailoProcessor] hailortcli not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            print("[HailoProcessor] hailortcli scan timed out")
            return False
        except Exception as e:
            print(f"[HailoProcessor] Error checking Hailo device: {e}")
            return False
    
    def _connect_camera(self, camera_name: str, rtsp_url: str) -> Optional[cv2.VideoCapture]:
        """
        Connect to a camera's RTSP stream.
        
        Args:
            camera_name: Name of the camera
            rtsp_url: RTSP stream URL
            
        Returns:
            VideoCapture object if successful, None otherwise
        """
        try:
            print(f"[HailoProcessor] Connecting to {camera_name}: {rtsp_url[:30]}...")
            
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            
            if cap.isOpened():
                # Test read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    print(f"[HailoProcessor] Connected to {camera_name} ({width}x{height})")
                    return cap
                else:
                    print(f"[HailoProcessor] Failed to read frame from {camera_name}")
                    cap.release()
                    return None
            else:
                print(f"[HailoProcessor] Failed to open stream for {camera_name}")
                return None
                
        except Exception as e:
            print(f"[HailoProcessor] Error connecting to {camera_name}: {e}")
            return None
    
    def _detect_faces_opencv(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using OpenCV's Haar Cascade (CPU fallback).
        
        This is used when Hailo is not available or as a fallback.
        
        Args:
            frame: OpenCV frame (BGR format)
            
        Returns:
            List of face bounding boxes as (x, y, w, h)
        """
        try:
            # Convert to grayscale for Haar Cascade
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Load Haar Cascade classifier
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=self.min_face_size
            )
            
            return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]
            
        except Exception as e:
            print(f"[HailoProcessor] Error in OpenCV face detection: {e}")
            return []
    
    def _detect_faces_hailo(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using Hailo AI HAT+.
        
        This uses the Hailo accelerator for high-performance face detection.
        
        Args:
            frame: OpenCV frame (BGR format)
            
        Returns:
            List of face bounding boxes as (x, y, w, h)
        """
        return self.face_detector.detect_faces(frame)
    
    def _save_snapshot(self, frame: np.ndarray, camera_name: str, timestamp: datetime) -> str:
        """
        Save a snapshot of the detected face.
        
        Args:
            frame: OpenCV frame
            camera_name: Name of the camera
            timestamp: Timestamp of the detection
            
        Returns:
            Path to the saved snapshot
        """
        try:
            # Generate filename
            ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{camera_name}_{ts_str}.jpg"
            filepath = os.path.join(self.snapshot_dir, filename)
            
            # Save image
            cv2.imwrite(filepath, frame)
            
            return filepath
            
        except Exception as e:
            print(f"[HailoProcessor] Error saving snapshot: {e}")
            return ""
    
    def _process_camera_stream(self, camera_name: str, rtsp_url: str):
        """
        Process a single camera stream in a dedicated thread.
        
        Args:
            camera_name: Name of the camera
            rtsp_url: RTSP stream URL
        """
        print(f"[HailoProcessor] Starting processing thread for {camera_name}")
        
        cap = self._connect_camera(camera_name, rtsp_url)
        if not cap:
            print(f"[HailoProcessor] Failed to start processing for {camera_name}")
            return
        
        last_detection_time = 0
        frame_count = 0
        
        try:
            while self.running:
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    print(f"[HailoProcessor] Lost connection to {camera_name}, reconnecting...")
                    cap.release()
                    time.sleep(5)
                    cap = self._connect_camera(camera_name, rtsp_url)
                    if not cap:
                        break
                    continue
                
                frame_count += 1
                current_time = time.time()
                
                # Process frame at specified interval
                if current_time - last_detection_time >= self.detection_interval:
                    last_detection_time = current_time
                    
                    # Detect faces
                    if self.hailo_available:
                        faces = self._detect_faces_hailo(frame)
                    else:
                        faces = self._detect_faces_opencv(frame)
                    
                    # Process each detected face
                    for (x, y, w, h) in faces:
                        tz = pytz.timezone(TIMEZONE)
                        timestamp = datetime.now(tz)
                        
                        # Save snapshot
                        snapshot_path = self._save_snapshot(frame, camera_name, timestamp)
                        
                        # Record sighting (unknown visitor for now)
                        self.db.add_sighting(
                            visitor_id=None,  # Unknown visitor
                            camera_name=camera_name,
                            timestamp=timestamp,
                            confidence=0.0,  # No recognition yet
                            snapshot_path=snapshot_path
                        )
                        
                        print(f"[HailoProcessor] Face detected on {camera_name} at {timestamp.strftime('%H:%M:%S')}")
                
                # Small delay to prevent CPU overload
                time.sleep(0.01)
                
        except Exception as e:
            print(f"[HailoProcessor] Error processing {camera_name}: {e}")
        finally:
            cap.release()
            print(f"[HailoProcessor] Stopped processing thread for {camera_name}")
    
    def start(self):
        """Start processing all configured cameras"""
        if self.running:
            print("[HailoProcessor] Already running")
            return
        
        self.running = True
        
        # Start a thread for each camera
        for camera_name, rtsp_url in CAMERAS.items():
            thread = threading.Thread(
                target=self._process_camera_stream,
                args=(camera_name, rtsp_url),
                daemon=True
            )
            thread.start()
            self.camera_threads[camera_name] = thread
        
        print(f"[HailoProcessor] Started processing {len(CAMERAS)} camera(s)")
    
    def stop(self):
        """Stop processing all cameras"""
        if not self.running:
            print("[HailoProcessor] Not running")
            return
        
        print("[HailoProcessor] Stopping...")
        self.running = False
        
        # Wait for all threads to finish
        for camera_name, thread in self.camera_threads.items():
            thread.join(timeout=5)
            print(f"[HailoProcessor] Stopped thread for {camera_name}")
        
        self.camera_threads.clear()
        
        # Stop the face detector pipeline
        self.face_detector.stop()
        
        print("[HailoProcessor] Stopped")
    
    def get_status(self) -> Dict:
        """
        Get current processor status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "running": self.running,
            "hailo_available": self.hailo_available,
            "active_cameras": len(self.camera_threads),
            "camera_names": list(self.camera_threads.keys())
        }


def get_processor():
    """
    Get the Hailo processor instance.
    
    Returns:
        HailoProcessor instance
    """
    return HailoProcessor()


# Test function
def test_hailo_processor(duration_seconds: int = 30):
    """
    Run the Hailo processor for a specified duration.
    
    Args:
        duration_seconds: How long to run the test
    """
    print(f"Testing Hailo processor for {duration_seconds} seconds...")
    
    processor = get_processor()
    processor.start()
    
    try:
        time.sleep(duration_seconds)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        processor.stop()
    
    print("\nTest complete. Check the database for sightings.")


if __name__ == "__main__":
    # Run a test
    test_hailo_processor(duration_seconds=30)
