"""
SeeWhozThere - Hailo Face Detector v4 (Correct API Usage)

This version properly manages the Hailo inference pipeline lifecycle:
- Activates network group once
- Creates InferVStreams once
- Reuses pipeline for all inferences
- Properly cleans up resources

Performance Target: 70-100 FPS on Hailo-8L
"""

import os
import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import time
import threading

try:
    import hailo_platform as hpf
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False
    print("[HailoFaceDetector] Warning: hailo_platform not available")

from app.retinaface_postprocessor import RetinaFacePostProcessor


class HailoFaceDetectorComplete:
    """
    Complete Hailo face detector with proper pipeline management.
    
    Key Architecture:
    1. Initialize once: Load model, create pipeline
    2. Start once: Activate network, create inference streams
    3. Detect many: Reuse pipeline for all frames
    4. Stop once: Clean up resources
    
    This matches the Hailo API's expected usage pattern.
    """
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.6):
        """
        Initialize the Hailo face detector.
        
        Args:
            model_path: Path to the .hef model file
            confidence_threshold: Minimum confidence for detections (0.0-1.0)
        """
        if not HAILO_AVAILABLE:
            raise ImportError("hailo_platform module not available. Please install HailoRT.")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.is_started = False
        self.lock = threading.Lock()
        
        print(f"[HailoFaceDetector] Loading model: {model_path}")
        
        # Load HEF file
        self.hef = hpf.HEF(model_path)
        
        # Create virtual device
        self.target = hpf.VDevice()
        
        # Configure network
        configure_params = hpf.ConfigureParams.create_from_hef(
            self.hef,
            interface=hpf.HailoStreamInterface.PCIe
        )
        network_groups = self.target.configure(self.hef, configure_params)
        
        if len(network_groups) != 1:
            raise ValueError(f"Expected 1 network group, got {len(network_groups)}")
        
        self.network_group = network_groups[0]
        self.network_group_params = self.network_group.create_params()
        
        # Get input/output information
        self.input_vstream_info = self.hef.get_input_vstream_infos()[0]
        self.output_vstream_infos = self.hef.get_output_vstream_infos()
        
        # Get input shape
        self.input_shape = self.input_vstream_info.shape
        self.input_height = self.input_shape[0]
        self.input_width = self.input_shape[1]
        
        # Create vstream parameters
        self.input_vstreams_params = hpf.InputVStreamParams.make_from_network_group(
            self.network_group,
            quantized=False,
            format_type=hpf.FormatType.UINT8
        )
        self.output_vstreams_params = hpf.OutputVStreamParams.make_from_network_group(
            self.network_group,
            quantized=False,
            format_type=hpf.FormatType.FLOAT32
        )
        
        # Initialize post-processor
        self.postprocessor = RetinaFacePostProcessor(
            input_width=self.input_width,
            input_height=self.input_height,
            confidence_threshold=confidence_threshold,
            nms_threshold=0.4
        )
        
        print(f"[HailoFaceDetector] ✅ Model loaded successfully")
        print(f"[HailoFaceDetector] Input shape: {self.input_shape}")
        print(f"[HailoFaceDetector] Output layers: {len(self.output_vstream_infos)}")
        
        # Performance tracking
        self.frame_count = 0
        self.total_inference_time = 0
        self.total_postprocess_time = 0
        
        # Pipeline resources (created in start())
        self.network_group_activated = None
        self.infer_pipeline = None
    
    def start(self):
        """
        Start the inference pipeline.
        
        This activates the network group and creates the inference streams.
        Must be called before detect_faces().
        """
        if self.is_started:
            print("[HailoFaceDetector] Already started")
            return
        
        print("[HailoFaceDetector] Starting inference pipeline...")
        
        # Activate network group
        self.network_group_activated = self.network_group.activate(self.network_group_params)
        self.network_group_activated.__enter__()
        
        # Create inference streams
        self.infer_pipeline = hpf.InferVStreams(
            self.network_group,
            self.input_vstreams_params,
            self.output_vstreams_params
        )
        self.infer_pipeline.__enter__()
        
        self.is_started = True
        print("[HailoFaceDetector] ✅ Pipeline started and ready!")
    
    def stop(self):
        """
        Stop the inference pipeline and clean up resources.
        """
        if not self.is_started:
            return
        
        print("[HailoFaceDetector] Stopping inference pipeline...")
        
        # Clean up inference streams
        if self.infer_pipeline:
            try:
                self.infer_pipeline.__exit__(None, None, None)
            except Exception as e:
                print(f"[HailoFaceDetector] Error closing infer pipeline: {e}")
            self.infer_pipeline = None
        
        # Deactivate network group
        if self.network_group_activated:
            try:
                self.network_group_activated.__exit__(None, None, None)
            except Exception as e:
                print(f"[HailoFaceDetector] Error deactivating network: {e}")
            self.network_group_activated = None
        
        self.is_started = False
        
        # Print final stats
        stats = self.get_performance_stats()
        if stats['frames_processed'] > 0:
            print(f"\n[HailoFaceDetector] 📊 FINAL PERFORMANCE:")
            print(f"  Total frames: {stats['frames_processed']}")
            print(f"  Average FPS: {stats['fps']}")
            print(f"  Average latency: {stats['avg_total_ms']}ms\n")
        
        print("[HailoFaceDetector] ✅ Pipeline stopped")
    
    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for Hailo inference.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            
        Returns:
            Preprocessed frame ready for inference
        """
        # Resize to model input size
        resized = cv2.resize(frame, (self.input_width, self.input_height))
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Model expects UINT8 format
        return rgb.astype(np.uint8)
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in a frame using Hailo accelerator.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            
        Returns:
            List of face bounding boxes as (x, y, w, h)
        """
        if not self.is_started:
            raise RuntimeError("Pipeline not started. Call start() first.")
        
        original_height, original_width = frame.shape[:2]
        
        # Preprocess frame
        input_data = self.preprocess(frame)
        
        # Prepare input (add batch dimension)
        input_batch = np.expand_dims(input_data, axis=0)
        input_dict = {self.input_vstream_info.name: input_batch}
        
        # Run inference (pipeline is already active!)
        with self.lock:  # Thread-safe inference
            inference_start = time.time()
            results = self.infer_pipeline.infer(input_dict)
            inference_time = (time.time() - inference_start) * 1000
        
        # Extract output tensors
        output_tensors = []
        for vstream_info in self.output_vstream_infos:
            output_tensors.append(results[vstream_info.name][0])  # Remove batch dimension
        
        # Post-process outputs
        postprocess_start = time.time()
        detections = self.postprocessor.process(output_tensors, (original_height, original_width))
        postprocess_time = (time.time() - postprocess_start) * 1000
        
        # Update performance stats
        self.frame_count += 1
        self.total_inference_time += inference_time
        self.total_postprocess_time += postprocess_time
        
        # Print performance every 30 frames
        if self.frame_count % 30 == 0:
            avg_inference = self.total_inference_time / self.frame_count
            avg_postprocess = self.total_postprocess_time / self.frame_count
            avg_total = avg_inference + avg_postprocess
            fps = 1000 / avg_total if avg_total > 0 else 0
            
            print(f"\n[HailoFaceDetector] ⚡ PERFORMANCE STATS (after {self.frame_count} frames):")
            print(f"  Inference time:     {avg_inference:.1f}ms")
            print(f"  Post-processing:    {avg_postprocess:.1f}ms")
            print(f"  Total per frame:    {avg_total:.1f}ms")
            print(f"  FPS:                {fps:.1f}")
            print(f"  Faces detected:     {len(detections)}\n")
        
        # Convert to (x, y, w, h) format
        faces = []
        for det in detections:
            x, y, w, h = det['bbox']
            faces.append((int(x), int(y), int(w), int(h)))
        
        return faces
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics."""
        if self.frame_count == 0:
            return {
                'frames_processed': 0,
                'avg_inference_ms': 0,
                'avg_postprocess_ms': 0,
                'avg_total_ms': 0,
                'fps': 0
            }
        
        avg_inference = self.total_inference_time / self.frame_count
        avg_postprocess = self.total_postprocess_time / self.frame_count
        avg_total = avg_inference + avg_postprocess
        fps = 1000 / avg_total if avg_total > 0 else 0
        
        return {
            'frames_processed': self.frame_count,
            'avg_inference_ms': round(avg_inference, 2),
            'avg_postprocess_ms': round(avg_postprocess, 2),
            'avg_total_ms': round(avg_total, 2),
            'fps': round(fps, 1)
        }
    
    def __del__(self):
        """Cleanup Hailo resources"""
        self.stop()


class HailoFaceDetectorSimple:
    """Simplified face detector using OpenCV (fallback)."""
    
    def __init__(self, confidence_threshold: float = 0.6):
        """Initialize simplified face detector."""
        self.confidence_threshold = confidence_threshold
        
        print("[HailoFaceDetectorSimple] Initializing OpenCV face detector")
        
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.min_face_size = (50, 50)
        
        print("[HailoFaceDetectorSimple] Ready")
    
    def start(self):
        """No-op for compatibility"""
        pass
    
    def stop(self):
        """No-op for compatibility"""
        pass
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using OpenCV."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=self.min_face_size
        )
        
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]


def create_face_detector(model_path: str = "models/retinaface_mobilenet_v1.hef",
                        confidence_threshold: float = 0.6,
                        use_hailo: bool = True):
    """
    Factory function to create the best available face detector.
    
    Args:
        model_path: Path to Hailo .hef model
        confidence_threshold: Detection confidence threshold
        use_hailo: Whether to try using Hailo (True) or use OpenCV directly (False)
        
    Returns:
        Face detector instance
    """
    if use_hailo and HAILO_AVAILABLE and os.path.exists(model_path):
        try:
            print("[create_face_detector] 🚀 Initializing Hailo AI accelerator...")
            detector = HailoFaceDetectorComplete(model_path, confidence_threshold)
            print("[create_face_detector] ✅ Hailo detector ready!")
            return detector
        except Exception as e:
            print(f"[create_face_detector] ❌ Failed to initialize Hailo: {e}")
            print("[create_face_detector] Falling back to OpenCV")
    else:
        if not HAILO_AVAILABLE:
            print("[create_face_detector] Hailo not available")
        elif not os.path.exists(model_path):
            print(f"[create_face_detector] Model not found: {model_path}")
        print("[create_face_detector] Using OpenCV detector")
    
    return HailoFaceDetectorSimple(confidence_threshold)
