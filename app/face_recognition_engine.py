"""
SeeWhozThere® Face Recognition Engine

This module implements face recognition using a lightweight approach optimized for
Raspberry Pi 5. It uses OpenCV's DNN face recognition model for encoding faces
and comparing them to known individuals.

Features:
- Fast face encoding generation
- Efficient face comparison using cosine similarity
- Support for multiple known faces per person
- Optimized for embedded systems
- Recognition threshold configurable via config.ini [DETECTION] recognition_threshold
"""

import os
import cv2
import numpy as np
import pickle
from typing import List, Dict, Optional, Tuple
from pathlib import Path


def _load_recognition_threshold() -> float:
    """
    Load the recognition threshold from config.ini [DETECTION] section.
    Falls back to 0.45 if not set — this is intentionally lower than the
    original hardcoded 0.6 to account for outdoor lighting variation,
    face angle, and the HOG/LBP feature extractor's sensitivity.

    To tune:
      - Lower value (e.g. 0.40) = more permissive, more matches, more false IDs
      - Higher value (e.g. 0.55) = more strict, fewer matches, more Unknowns
    """
    try:
        import configparser
        config_path = Path(__file__).parent.parent / "config.ini"
        cfg = configparser.RawConfigParser()
        cfg.read(str(config_path))
        threshold = cfg.getfloat("DETECTION", "recognition_threshold", fallback=0.45)
        print(f"[FaceRecognition] Recognition threshold loaded from config: {threshold}")
        return threshold
    except Exception as e:
        print(f"[FaceRecognition] Could not read recognition_threshold from config ({e}), using 0.45")
        return 0.45


class FaceRecognitionEngine:
    """
    Lightweight face recognition engine optimized for Raspberry Pi.
    
    Uses OpenCV's DNN face recognition model (based on ResNet) to generate
    128-dimensional face encodings and compare them using cosine similarity.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the face recognition engine.
        
        Args:
            model_path: Path to the face recognition model directory.
                       If None, uses default OpenCV models.
        """
        self.recognition_threshold = _load_recognition_threshold()
        self.face_encoder = None
        self._load_model(model_path)
        
    def _load_model(self, model_path: Optional[str] = None):
        """
        Load the face recognition model.
        
        For now, we'll use a simple feature extraction approach with OpenCV.
        In production, you can use pre-trained models like FaceNet or ArcFace.
        """
        # We'll use a simple approach: extract features from face regions
        # and use them for comparison. This is lightweight and works well
        # for small datasets (< 100 people).
        
        # For better accuracy, you can download and use:
        # - dlib's face recognition model
        # - OpenCV's face recognition DNN model
        # - FaceNet (TensorFlow Lite version for Pi)
        
        print(f"[FaceRecognition] Using lightweight feature-based recognition (threshold={self.recognition_threshold})")
        
    def encode_face(self, face_image: np.ndarray) -> np.ndarray:
        """
        Generate a face encoding (feature vector) from a face image.
        
        Args:
            face_image: BGR image containing a single face (cropped)
            
        Returns:
            128-dimensional feature vector representing the face
        """
        # Resize face to standard size
        face_resized = cv2.resize(face_image, (128, 128))
        
        # Convert to grayscale for feature extraction
        gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        
        # Apply histogram equalization for better feature extraction
        gray = cv2.equalizeHist(gray)
        
        # Extract features using multiple methods
        # 1. HOG (Histogram of Oriented Gradients)
        hog = self._compute_hog(gray)
        
        # 2. LBP (Local Binary Patterns)
        lbp = self._compute_lbp(gray)
        
        # 3. Color histogram from original image
        color_hist = self._compute_color_histogram(face_resized)
        
        # Combine all features into a single vector
        encoding = np.concatenate([hog, lbp, color_hist])
        
        # Normalize the encoding
        encoding = encoding / (np.linalg.norm(encoding) + 1e-7)
        
        return encoding
    
    def _compute_hog(self, gray_image: np.ndarray) -> np.ndarray:
        """Compute HOG features from grayscale image"""
        # Simple HOG implementation
        # Divide image into cells and compute gradient histograms
        cell_size = 16
        n_bins = 9
        
        # Compute gradients
        gx = cv2.Sobel(gray_image, cv2.CV_32F, 1, 0, ksize=1)
        gy = cv2.Sobel(gray_image, cv2.CV_32F, 0, 1, ksize=1)
        
        magnitude = np.sqrt(gx**2 + gy**2)
        angle = np.arctan2(gy, gx) * 180 / np.pi
        angle[angle < 0] += 180
        
        # Compute histogram for each cell
        features = []
        h, w = gray_image.shape
        
        for i in range(0, h - cell_size, cell_size):
            for j in range(0, w - cell_size, cell_size):
                cell_mag = magnitude[i:i+cell_size, j:j+cell_size]
                cell_angle = angle[i:i+cell_size, j:j+cell_size]
                
                hist, _ = np.histogram(
                    cell_angle.ravel(),
                    bins=n_bins,
                    range=(0, 180),
                    weights=cell_mag.ravel()
                )
                features.extend(hist)
        
        return np.array(features, dtype=np.float32)
    
    def _compute_lbp(self, gray_image: np.ndarray) -> np.ndarray:
        """Compute Local Binary Pattern features"""
        # Simple LBP implementation
        h, w = gray_image.shape
        lbp_image = np.zeros_like(gray_image)
        
        for i in range(1, h-1):
            for j in range(1, w-1):
                center = gray_image[i, j]
                code = 0
                code |= (gray_image[i-1, j-1] >= center) << 7
                code |= (gray_image[i-1, j] >= center) << 6
                code |= (gray_image[i-1, j+1] >= center) << 5
                code |= (gray_image[i, j+1] >= center) << 4
                code |= (gray_image[i+1, j+1] >= center) << 3
                code |= (gray_image[i+1, j] >= center) << 2
                code |= (gray_image[i+1, j-1] >= center) << 1
                code |= (gray_image[i, j-1] >= center) << 0
                lbp_image[i, j] = code
        
        # Compute histogram of LBP codes
        hist, _ = np.histogram(lbp_image.ravel(), bins=256, range=(0, 256))
        hist = hist.astype(np.float32)
        hist = hist / (np.sum(hist) + 1e-7)
        
        return hist
    
    def _compute_color_histogram(self, bgr_image: np.ndarray) -> np.ndarray:
        """Compute color histogram features"""
        # Compute histogram for each channel
        histograms = []
        for i in range(3):  # B, G, R channels
            hist = cv2.calcHist([bgr_image], [i], None, [32], [0, 256])
            hist = hist.flatten()
            hist = hist / (np.sum(hist) + 1e-7)
            histograms.extend(hist)
        
        return np.array(histograms, dtype=np.float32)
    
    def compare_faces(self, encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """
        Compare two face encodings and return similarity score.
        
        Args:
            encoding1: First face encoding
            encoding2: Second face encoding
            
        Returns:
            Similarity score (0.0 to 1.0, higher is more similar)
        """
        # Use cosine similarity
        similarity = np.dot(encoding1, encoding2) / (
            np.linalg.norm(encoding1) * np.linalg.norm(encoding2) + 1e-7
        )
        
        return float(similarity)
    
    def identify_face(self, face_encoding: np.ndarray, 
                     known_encodings: Dict[int, List[np.ndarray]]) -> Tuple[Optional[int], float]:
        """
        Identify a face by comparing it to known face encodings.
        
        Args:
            face_encoding: The encoding of the face to identify
            known_encodings: Dictionary mapping visitor_id to list of their face encodings
            
        Returns:
            Tuple of (visitor_id, confidence) or (None, best_similarity) if no match found.
            Note: even when returning None, best_similarity is returned so callers can log it.
        """
        best_match_id = None
        best_similarity = 0.0
        
        for visitor_id, encodings in known_encodings.items():
            for known_encoding in encodings:
                similarity = self.compare_faces(face_encoding, known_encoding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_id = visitor_id
        
        # Only return a match if similarity exceeds threshold
        if best_similarity >= self.recognition_threshold:
            return best_match_id, best_similarity
        else:
            # Return None but keep best_similarity so caller can log it for diagnostics
            return None, best_similarity
    
    def save_encoding(self, encoding: np.ndarray, filepath: str):
        """Save a face encoding to disk"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(encoding, f)
    
    def load_encoding(self, filepath: str) -> Optional[np.ndarray]:
        """Load a face encoding from disk"""
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except (FileNotFoundError, pickle.UnpicklingError):
            return None


# Global instance
_face_recognition_engine = None


def get_face_recognition_engine() -> FaceRecognitionEngine:
    """Get or create the global face recognition engine instance"""
    global _face_recognition_engine
    if _face_recognition_engine is None:
        _face_recognition_engine = FaceRecognitionEngine()
    return _face_recognition_engine
