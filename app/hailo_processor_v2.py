"""
SeeWhozThere® Hailo AI Processor Module v2

Enhanced version with face recognition capabilities.

This module implements:
1. Face detection using Hailo AI HAT+
2. Face recognition to identify known people
3. Continuous 24/7 monitoring
4. Auto-recovery from errors
5. Performance monitoring

Hardware Requirements:
- Raspberry Pi 5
- Raspberry Pi AI HAT+ (Hailo-8L 13 TOPS or Hailo-8 26 TOPS)
- IP camera with RTSP support (e.g., Tapo C310)

Performance:
- Face detection: 300-400 FPS (with Hailo-8L)
- Face recognition: Real-time
- Multiple camera support
- Minimal latency
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
import traceback

from app.config import get_cameras, TIMEZONE, DETECTION_COOLDOWN_SECONDS, DETECTION_CONFIDENCE_THRESHOLD, DETECTION_MIN_FACE_WIDTH, DETECTION_MIN_FACE_HEIGHT
from app.database import get_db
from app.hailo_face_detector_v4 import create_face_detector
from app.face_recognition_engine import get_face_recognition_engine
from app.telegram_notifier import send_unknown_face_alert, send_known_face_alert


class HailoProcessorV2:
    """
    Enhanced real-time face detection and recognition processor.
    
    Features:
    1. Face detection using Hailo AI accelerator
    2. Face recognition to identify known people
    3. Continuous monitoring with auto-recovery
    4. Performance tracking
    5. Thread-safe operation
    """
    
    def __init__(self):
        """Initialize the enhanced Hailo processor"""
        self.db = get_db()
        self.running = False
        self.camera_threads = {}
        self.camera_urls = {}  # Stores rtsp_url per camera for watchdog restarts
        self.frame_queues = {}
        self.hailo_available = self._check_hailo_device()
        
        # Face detection parameters — read from config.ini [DETECTION] section
        self.detection_interval = 1.0  # Process every N seconds per camera (frame rate throttle)
        self.snapshot_cooldown = DETECTION_COOLDOWN_SECONDS  # Min seconds between saved snapshots per camera
        self.confidence_threshold = DETECTION_CONFIDENCE_THRESHOLD
        self.min_face_size = (DETECTION_MIN_FACE_WIDTH, DETECTION_MIN_FACE_HEIGHT)  # Read from config.ini [DETECTION]
        
        # Per-camera last-snapshot timestamp (used to enforce cooldown)
        self.last_snapshot_time: Dict[str, float] = {}
        
        # Snapshot storage
        self.snapshot_dir = "data/snapshots"
        self.encodings_dir = "data/encodings"
        os.makedirs(self.snapshot_dir, exist_ok=True)
        os.makedirs(self.encodings_dir, exist_ok=True)
        
        # Initialize face detector with Hailo support
        model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'retinaface_mobilenet_v1.hef')
        self.face_detector = create_face_detector(
            model_path=model_path,
            confidence_threshold=self.confidence_threshold,
            use_hailo=self.hailo_available
        )
        
        # Initialize face recognition engine
        self.face_recognition = get_face_recognition_engine()
        
        # Load known face encodings from database
        self.known_encodings = {}
        self._load_known_faces()
        
        # Start the face detector pipeline
        self.face_detector.start()
        
        # Performance tracking
        self.stats = {
            'total_detections': 0,
            'total_recognitions': 0,
            'unknown_faces': 0,
            'start_time': None
        }
        
        print(f"[HailoProcessorV2] Initialized")
        print(f"[HailoProcessorV2] Hailo device available: {self.hailo_available}")
        print(f"[HailoProcessorV2] Face detector: {type(self.face_detector).__name__}")
        print(f"[HailoProcessorV2] Known people: {len(self.known_encodings)}")
    
    def _check_hailo_device(self) -> bool:
        """
        Check if Hailo AI HAT+ is available and functioning.
        
        Returns:
            True if Hailo device is detected, False otherwise
        """
        try:
            # Check for /dev/hailo0
            if os.path.exists("/dev/hailo0"):
                print("[HailoProcessorV2] Found /dev/hailo0")
                
                # Try to run hailortcli scan
                result = subprocess.run(
                    ["hailortcli", "scan"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and "Device:" in result.stdout:
                    print("[HailoProcessorV2] Hailo device verified via hailortcli")
                    return True
                else:
                    print("[HailoProcessorV2] hailortcli scan failed")
                    return False
            else:
                print("[HailoProcessorV2] /dev/hailo0 not found")
                return False
                
        except FileNotFoundError:
            print("[HailoProcessorV2] hailortcli not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            print("[HailoProcessorV2] hailortcli scan timed out")
            return False
        except Exception as e:
            print(f"[HailoProcessorV2] Error checking Hailo device: {e}")
            return False
    
    def _load_known_faces(self):
        """Load all known face encodings from the database"""
        try:
            visitors = self.db.get_all_visitors()
            self.known_encodings = {}
            
            for visitor in visitors:
                visitor_id = visitor['id']
                face_encoding_blob = visitor.get('face_encoding')
                
                if face_encoding_blob:
                    # Deserialize the encoding
                    encoding = np.frombuffer(face_encoding_blob, dtype=np.float32)
                    
                    if visitor_id not in self.known_encodings:
                        self.known_encodings[visitor_id] = []
                    
                    self.known_encodings[visitor_id].append(encoding)
            
            print(f"[HailoProcessorV2] Loaded {len(self.known_encodings)} known people")
            
        except Exception as e:
            print(f"[HailoProcessorV2] Error loading known faces: {e}")
            traceback.print_exc()
    
    def reload_known_faces(self):
        """Reload known face encodings (call after adding/updating people)"""
        print("[HailoProcessorV2] Reloading known faces...")
        self._load_known_faces()
    
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
            print(f"[HailoProcessorV2] Connecting to {camera_name}: {rtsp_url[:30]}...")
            
            cap = cv2.VideoCapture(rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            
            if cap.isOpened():
                # Test read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    print(f"[HailoProcessorV2] Connected to {camera_name} ({width}x{height})")
                    return cap
                else:
                    print(f"[HailoProcessorV2] Failed to read frame from {camera_name}")
                    cap.release()
                    return None
            else:
                print(f"[HailoProcessorV2] Failed to open stream for {camera_name}")
                return None
                
        except Exception as e:
            print(f"[HailoProcessorV2] Error connecting to {camera_name}: {e}")
            return None
    
    def _detect_faces_opencv(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using OpenCV's Haar Cascade (CPU fallback).
        
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
            print(f"[HailoProcessorV2] Error in OpenCV face detection: {e}")
            return []
    
    def _detect_faces_hailo(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using Hailo AI HAT+.
        
        Args:
            frame: OpenCV frame (BGR format)
            
        Returns:
            List of face bounding boxes as (x, y, w, h)
        """
        return self.face_detector.detect_faces(frame)
    
    def _recognize_face(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Tuple[Optional[int], float]:
        """
        Recognize a detected face.
        
        Args:
            frame: Full frame image
            bbox: Face bounding box (x, y, w, h)
            
        Returns:
            Tuple of (visitor_id, confidence) or (None, 0.0) if unknown
        """
        try:
            x, y, w, h = bbox
            
            # Extract face region with some padding
            padding = 20
            y1 = max(0, y - padding)
            y2 = min(frame.shape[0], y + h + padding)
            x1 = max(0, x - padding)
            x2 = min(frame.shape[1], x + w + padding)
            
            face_img = frame[y1:y2, x1:x2]
            
            if face_img.size == 0:
                return None, 0.0
            
            # Generate face encoding
            encoding = self.face_recognition.encode_face(face_img)
            
            # Compare with known faces
            if len(self.known_encodings) > 0:
                visitor_id, confidence = self.face_recognition.identify_face(
                    encoding, 
                    self.known_encodings
                )
                return visitor_id, confidence
            else:
                return None, 0.0
                
        except Exception as e:
            print(f"[HailoProcessorV2] Error in face recognition: {e}")
            traceback.print_exc()
            return None, 0.0
    
    def _save_snapshot(self, frame: np.ndarray, camera_name: str, timestamp: datetime,
                      bbox: Optional[Tuple[int, int, int, int]] = None) -> str:
        """
        Save a snapshot of the detected face.
        
        Args:
            frame: OpenCV frame
            camera_name: Name of the camera
            timestamp: Timestamp of the detection
            bbox: Optional bounding box to draw on the image
            
        Returns:
            Path to the saved snapshot
        """
        try:
            # Clone frame to avoid modifying original
            snapshot = frame.copy()
            
            # Draw bounding box if provided
            if bbox:
                x, y, w, h = bbox
                cv2.rectangle(snapshot, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Generate filename
            ts_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{camera_name}_{ts_str}.jpg"
            filepath = os.path.join(self.snapshot_dir, filename)
            
            # Save image
            cv2.imwrite(filepath, snapshot)
            
            return filepath
            
        except Exception as e:
            print(f"[HailoProcessorV2] Error saving snapshot: {e}")
            return ""
    
    def _process_camera_stream(self, camera_name: str, rtsp_url: str):
        """
        Process a single camera stream in a dedicated thread.
        
        Args:
            camera_name: Name of the camera
            rtsp_url: RTSP stream URL
        """
        print(f"[HailoProcessorV2] Starting processing thread for {camera_name}")
        
        cap = self._connect_camera(camera_name, rtsp_url)
        if not cap:
            print(f"[HailoProcessorV2] Failed to start processing for {camera_name}")
            return
        
        last_detection_time = 0
        frame_count = 0
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        try:
            while self.running:
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    reconnect_attempts += 1
                    print(f"[HailoProcessorV2] Lost connection to {camera_name} (attempt {reconnect_attempts}/{max_reconnect_attempts})")
                    
                    if reconnect_attempts >= max_reconnect_attempts:
                        print(f"[HailoProcessorV2] Max reconnection attempts reached for {camera_name}")
                        break
                    
                    cap.release()
                    time.sleep(5)
                    cap = self._connect_camera(camera_name, rtsp_url)
                    if not cap:
                        continue
                    reconnect_attempts = 0
                    continue
                
                # Reset reconnect counter on successful frame
                reconnect_attempts = 0
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
                    for bbox in faces:
                        tz = pytz.timezone(TIMEZONE)
                        timestamp = datetime.now(tz)
                        
                        # Enforce per-camera snapshot cooldown
                        last_snap = self.last_snapshot_time.get(camera_name, 0)
                        if current_time - last_snap < self.snapshot_cooldown:
                            continue  # Too soon — skip this detection
                        self.last_snapshot_time[camera_name] = current_time
                        
                        # Recognize face
                        visitor_id, confidence = self._recognize_face(frame, bbox)
                        
                        # Save snapshot with bounding box
                        snapshot_path = self._save_snapshot(frame, camera_name, timestamp, bbox)
                        
                        # Record sighting — capture the returned sighting_id
                        sighting_id = self.db.add_sighting(
                            visitor_id=visitor_id,
                            camera_name=camera_name,
                            timestamp=timestamp,
                            confidence=confidence,
                            snapshot_path=snapshot_path
                        )
                        
                        # Update stats and send Telegram notifications
                        self.stats['total_detections'] += 1
                        if visitor_id is not None:
                            self.stats['total_recognitions'] += 1
                            visitor = self.db.get_visitor(visitor_id)
                            visitor_name = visitor['name'] if visitor else 'Unknown'
                            print(f"[HailoProcessorV2] Recognized {visitor_name} on {camera_name} (confidence: {confidence:.2f})")
                            # Send Telegram alert for known visitor (fire-and-forget in background)
                            threading.Thread(
                                target=send_known_face_alert,
                                args=(visitor_name, camera_name, snapshot_path),
                                daemon=True
                            ).start()
                        else:
                            self.stats['unknown_faces'] += 1
                            print(f"[HailoProcessorV2] Unknown face detected on {camera_name}")
                            # Send Telegram alert for unknown face — pass sighting_id to enable
                            # inline identification buttons in the Telegram message.
                            threading.Thread(
                                target=send_unknown_face_alert,
                                args=(camera_name, snapshot_path, sighting_id),
                                daemon=True
                            ).start()
                
                # Small delay to prevent CPU overload
                time.sleep(0.01)
                
        except Exception as e:
            print(f"[HailoProcessorV2] Error processing {camera_name}: {e}")
            traceback.print_exc()
        finally:
            cap.release()
            print(f"[HailoProcessorV2] Stopped processing thread for {camera_name}")
    
    def start(self):
        """Start processing all configured cameras"""
        if self.running:
            print("[HailoProcessorV2] Already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Read cameras fresh from config.ini at start time so a service
        # restart always picks up the latest camera list.
        cameras = get_cameras()
        
        if not cameras:
            print("[HailoProcessorV2] WARNING: No cameras configured in config.ini [CAMERAS] section")
            print("[HailoProcessorV2] Add cameras via the Settings page or edit config.ini, then restart the service")
        
        # Start a thread for each camera
        for camera_name, rtsp_url in cameras.items():
            self.camera_urls[camera_name] = rtsp_url
            thread = threading.Thread(
                target=self._process_camera_stream,
                args=(camera_name, rtsp_url),
                daemon=True
            )
            thread.start()
            self.camera_threads[camera_name] = thread
        
        print(f"[HailoProcessorV2] Started processing {len(cameras)} camera(s)")
        
        # Start watchdog thread to automatically restart dead camera threads
        watchdog = threading.Thread(target=self._camera_watchdog, daemon=True)
        watchdog.start()
        print("[HailoProcessorV2] Camera watchdog started")
    
    def _camera_watchdog(self):
        """Watchdog: checks every 30s if any camera thread has died and restarts it automatically."""
        while self.running:
            time.sleep(30)
            if not self.running:
                break
            for camera_name, thread in list(self.camera_threads.items()):
                if not thread.is_alive():
                    rtsp_url = self.camera_urls.get(camera_name)
                    if rtsp_url:
                        print(f"[HailoProcessorV2] Watchdog: '{camera_name}' thread is dead — restarting in 10s...")
                        time.sleep(10)
                        if not self.running:
                            break
                        new_thread = threading.Thread(
                            target=self._process_camera_stream,
                            args=(camera_name, rtsp_url),
                            daemon=True
                        )
                        new_thread.start()
                        self.camera_threads[camera_name] = new_thread
                        print(f"[HailoProcessorV2] Watchdog: restarted thread for '{camera_name}'")
    
    def stop(self):
        """Stop processing all cameras"""
        if not self.running:
            print("[HailoProcessorV2] Not running")
            return
        
        print("[HailoProcessorV2] Stopping...")
        self.running = False
        
        # Wait for all threads to finish
        for camera_name, thread in self.camera_threads.items():
            thread.join(timeout=5)
            print(f"[HailoProcessorV2] Stopped thread for {camera_name}")
        
        self.camera_threads.clear()
        
        # Stop the face detector pipeline
        self.face_detector.stop()
        
        print("[HailoProcessorV2] Stopped")
    
    def get_status(self) -> Dict:
        """
        Get current processor status.
        
        Returns:
            Dictionary with status information
        """
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            "running": self.running,
            "hailo_available": self.hailo_available,
            "active_cameras": len(self.camera_threads),
            "camera_names": list(self.camera_threads.keys()),
            "known_people": len(self.known_encodings),
            "stats": {
                **self.stats,
                "uptime_seconds": uptime
            }
        }


# Global processor instance
_processor_instance = None


def get_processor() -> HailoProcessorV2:
    """
    Get or create the global processor instance.
    
    Returns:
        HailoProcessorV2 instance
    """
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = HailoProcessorV2()
    return _processor_instance


# Test function
def test_hailo_processor(duration_seconds: int = 30):
    """
    Run the Hailo processor for a specified duration.
    
    Args:
        duration_seconds: How long to run the test
    """
    print(f"Testing Hailo processor v2 for {duration_seconds} seconds...")
    
    processor = get_processor()
    processor.start()
    
    try:
        time.sleep(duration_seconds)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        processor.stop()
        
        # Print stats
        status = processor.get_status()
        print("\n=== Test Results ===")
        print(f"Total detections: {status['stats']['total_detections']}")
        print(f"Recognized faces: {status['stats']['total_recognitions']}")
        print(f"Unknown faces: {status['stats']['unknown_faces']}")
        print(f"Uptime: {status['stats']['uptime_seconds']:.1f} seconds")
    
    print("\nTest complete. Check the database for sightings.")


if __name__ == "__main__":
    # Run a test
    test_hailo_processor(duration_seconds=30)
