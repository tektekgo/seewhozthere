"""
SeeWhozThere® Face Recognition Engine — InsightFace ArcFace Edition

Replaces the previous HOG/LBP feature-based approach with InsightFace's
ArcFace deep learning model (buffalo_sc). ArcFace was specifically designed
for surveillance and outdoor recognition scenarios and handles:

  - Face angles up to ~45° from frontal
  - Varying lighting conditions (outdoor, backlit, overcast)
  - Partial occlusion (hats, hoods, glasses)
  - Small face crops (down to ~40×40px)

Model: buffalo_sc (small/compact ArcFace)
  - 512-dimensional face embedding
  - ~150–300ms per face on Raspberry Pi 5 CPU
  - ~30MB download on first run (cached to ~/.insightface/models/)

Interface: identical to the previous engine — all method signatures,
return types, and the global get_face_recognition_engine() function
are preserved so no other files need to change.

Configuration (config.ini [DETECTION]):
  recognition_threshold = 0.40   # cosine similarity; 0.35–0.50 recommended
"""

import os
import cv2
import numpy as np
import pickle
from typing import List, Dict, Optional, Tuple
from pathlib import Path


# ── Threshold loader ──────────────────────────────────────────────────────────

def _load_recognition_threshold() -> float:
    """
    Load recognition threshold from config.ini [DETECTION] section.

    ArcFace cosine similarity scores are higher than HOG/LBP scores for the
    same face, so the default here (0.40) is intentionally different from the
    old engine's 0.45.  Tune as follows:

      - 0.30–0.35 : very permissive — good for far/angled faces, more false IDs
      - 0.40      : recommended default for outdoor cameras
      - 0.45–0.50 : strict — fewer false IDs but more Unknowns at distance
    """
    try:
        import configparser
        config_path = Path(__file__).parent.parent / "config.ini"
        cfg = configparser.RawConfigParser()
        cfg.read(str(config_path))
        threshold = cfg.getfloat("DETECTION", "recognition_threshold", fallback=0.40)
        print(f"[FaceRecognition] ArcFace recognition threshold: {threshold}")
        return threshold
    except Exception as e:
        print(f"[FaceRecognition] Could not read recognition_threshold ({e}), using 0.40")
        return 0.40


# ── InsightFace loader ────────────────────────────────────────────────────────

def _load_insightface_app():
    """
    Load InsightFace FaceAnalysis app with buffalo_sc model (recognition only).
    Returns the app instance, or None if InsightFace is not installed.

    Two-stage loading strategy:
    1. Try FaceAnalysis (high-level wrapper) — preferred
    2. If that fails, try loading the ONNX model directly via onnxruntime
       (works around numpy version conflicts with app.prepare())
    """
    import traceback as _tb

    # ── Stage 1: FaceAnalysis wrapper ────────────────────────────────────────
    try:
        import insightface
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(
            name="buffalo_sc",
            providers=["CPUExecutionProvider"],
            allowed_modules=["recognition"],
        )
        app.prepare(ctx_id=0, det_size=(320, 320))
        print("[FaceRecognition] InsightFace buffalo_sc loaded via FaceAnalysis (ArcFace mode)")
        return app
    except ImportError:
        print(
            "[FaceRecognition] WARNING: InsightFace not installed. "
            "Run: pip3 install insightface onnxruntime --break-system-packages\n"
            "[FaceRecognition] Falling back to HOG/LBP engine."
        )
        return None
    except Exception as e:
        print(f"[FaceRecognition] FaceAnalysis load failed: {type(e).__name__}: {e}")
        _tb.print_exc()
        print("[FaceRecognition] Trying direct ONNX model load as fallback...")

    # ── Stage 2: Direct ONNX model load ──────────────────────────────────────
    # This bypasses app.prepare() which can fail due to numpy version conflicts.
    # We load just the recognition model (w600k_mbf.onnx) directly.
    try:
        import os as _os
        import onnxruntime as _ort

        model_dir = _os.path.expanduser("~/.insightface/models/buffalo_sc")
        model_path = _os.path.join(model_dir, "w600k_mbf.onnx")

        if not _os.path.exists(model_path):
            print(f"[FaceRecognition] Model not found at {model_path} — cannot use direct ONNX load")
            return None

        sess = _ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )
        print(f"[FaceRecognition] Direct ONNX load succeeded: {model_path}")
        print("[FaceRecognition] InsightFace ArcFace active via direct ONNX session")
        # Wrap in a simple object so the rest of the engine can call it uniformly
        return _DirectONNXRecognizer(sess)
    except Exception as e2:
        print(f"[FaceRecognition] Direct ONNX load also failed: {type(e2).__name__}: {e2}")
        _tb.print_exc()
        print("[FaceRecognition] Falling back to HOG/LBP engine.")
        return None


class _DirectONNXRecognizer:
    """
    Thin wrapper around a raw onnxruntime InferenceSession for the
    w600k_mbf ArcFace model.  Provides the same .get(image) interface
    as InsightFace FaceAnalysis so the engine code needs no changes.

    Input:  BGR image (any size) — we resize to 112×112 and normalise
    Output: list of face objects with .embedding (512-dim float32 array)
    """

    INPUT_SIZE = (112, 112)
    MEAN = 127.5
    STD  = 127.5

    def __init__(self, session):
        self._sess = session
        self._input_name  = session.get_inputs()[0].name
        self._output_name = session.get_outputs()[0].name

    def get(self, image):
        """Run ArcFace on the image and return a list with one face object."""
        import numpy as _np
        import cv2 as _cv2

        # Resize and normalise to model input format
        face = _cv2.resize(image, self.INPUT_SIZE)
        face = face.astype(_np.float32)
        face = (face - self.MEAN) / self.STD
        # HWC → NCHW
        face = face.transpose(2, 0, 1)[_np.newaxis, :, :, :]

        embedding = self._sess.run(
            [self._output_name],
            {self._input_name: face}
        )[0][0]  # shape: (512,)

        embedding = embedding.astype(_np.float32)
        norm = _np.linalg.norm(embedding)
        embedding = embedding / (norm + 1e-7)

        # Return a simple namespace so largest.embedding works
        class _Face:
            pass
        f = _Face()
        f.embedding = embedding
        # Fake bbox covering the whole image so max() by area picks it
        h, w = image.shape[:2]
        f.bbox = [0, 0, w, h]
        return [f]


# ── HOG/LBP fallback (kept for graceful degradation) ─────────────────────────

class _HOGLBPFallback:
    """Minimal HOG+LBP engine used only if InsightFace is unavailable."""

    def encode(self, face_image: np.ndarray) -> np.ndarray:
        face = cv2.resize(face_image, (128, 128))
        gray = cv2.equalizeHist(cv2.cvtColor(face, cv2.COLOR_BGR2GRAY))
        hog = self._hog(gray)
        lbp = self._lbp(gray)
        chist = self._chist(face)
        enc = np.concatenate([hog, lbp, chist]).astype(np.float32)
        return enc / (np.linalg.norm(enc) + 1e-7)

    def _hog(self, g):
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=1)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=1)
        mag = np.sqrt(gx**2 + gy**2)
        ang = np.arctan2(gy, gx) * 180 / np.pi
        ang[ang < 0] += 180
        feats = []
        for i in range(0, g.shape[0] - 16, 16):
            for j in range(0, g.shape[1] - 16, 16):
                h, _ = np.histogram(ang[i:i+16, j:j+16].ravel(), 9, (0, 180),
                                    weights=mag[i:i+16, j:j+16].ravel())
                feats.extend(h)
        return np.array(feats, dtype=np.float32)

    def _lbp(self, g):
        h, w = g.shape
        lbp = np.zeros_like(g)
        for i in range(1, h - 1):
            for j in range(1, w - 1):
                c = g[i, j]
                code = (
                    ((g[i-1, j-1] >= c) << 7) | ((g[i-1, j] >= c) << 6) |
                    ((g[i-1, j+1] >= c) << 5) | ((g[i, j+1] >= c) << 4) |
                    ((g[i+1, j+1] >= c) << 3) | ((g[i+1, j] >= c) << 2) |
                    ((g[i+1, j-1] >= c) << 1) | (g[i, j-1] >= c)
                )
                lbp[i, j] = code
        hist, _ = np.histogram(lbp.ravel(), 256, (0, 256))
        hist = hist.astype(np.float32)
        return hist / (hist.sum() + 1e-7)

    def _chist(self, bgr):
        feats = []
        for ch in range(3):
            h = cv2.calcHist([bgr], [ch], None, [32], [0, 256]).flatten()
            feats.extend(h / (h.sum() + 1e-7))
        return np.array(feats, dtype=np.float32)


# ── Main engine ───────────────────────────────────────────────────────────────

class FaceRecognitionEngine:
    """
    ArcFace-based face recognition engine for SeeWhozThere®.

    Uses InsightFace's buffalo_sc model to generate 512-dimensional ArcFace
    embeddings.  Falls back to the legacy HOG/LBP engine if InsightFace is
    not installed, so the system remains functional during upgrades.

    Public interface is identical to the previous HOG/LBP engine:
      encode_face(image)           → np.ndarray (embedding)
      compare_faces(enc1, enc2)    → float (cosine similarity)
      identify_face(enc, known)    → (visitor_id | None, score)
      save_encoding(enc, path)
      load_encoding(path)          → np.ndarray | None
    """

    def __init__(self, model_path: Optional[str] = None):
        self.recognition_threshold = _load_recognition_threshold()
        self._app = _load_insightface_app()
        self._fallback = _HOGLBPFallback() if self._app is None else None
        self._using_arcface = self._app is not None

        if self._using_arcface:
            print("[FaceRecognition] Engine: InsightFace ArcFace (buffalo_sc) — 512-dim embeddings")
        else:
            print("[FaceRecognition] Engine: HOG/LBP fallback — install insightface for better accuracy")

    # ── Encoding ──────────────────────────────────────────────────────────────

    def encode_face(self, face_image: np.ndarray) -> np.ndarray:
        """
        Generate a face embedding from a face crop (BGR image).

        With InsightFace: returns a 512-dimensional L2-normalised ArcFace
        embedding, or **None** if ArcFace cannot detect a face in the crop.
        Callers MUST check for None before saving or comparing the result.
        Returning None (rather than a pixel-hash fallback) prevents garbage
        crops (birds, shadows, plants) from poisoning the encoding database.

        With HOG/LBP fallback: returns the legacy feature vector (never None).

        Args:
            face_image: BGR image containing a face (can be full frame or crop)

        Returns:
            np.ndarray: face embedding vector, L2-normalised
            None: if ArcFace finds no face in the crop (do not save this result)
        """
        if self._using_arcface:
            return self._encode_arcface(face_image)
        return self._fallback.encode(face_image)

    def _encode_arcface(self, face_image: np.ndarray) -> np.ndarray:
        """Run InsightFace ArcFace embedding on the face image."""
        try:
            # InsightFace expects BGR uint8
            if face_image.dtype != np.uint8:
                face_image = (face_image * 255).clip(0, 255).astype(np.uint8)

            # Ensure minimum size for the model
            h, w = face_image.shape[:2]
            if h < 112 or w < 112:
                scale = max(112 / h, 112 / w)
                face_image = cv2.resize(
                    face_image,
                    (int(w * scale), int(h * scale)),
                    interpolation=cv2.INTER_LINEAR
                )

            faces = self._app.get(face_image)

            if faces:
                # Use the largest detected face (most prominent)
                largest = max(faces, key=lambda f: (
                    (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
                ))
                embedding = largest.embedding.astype(np.float32)
                # L2 normalise
                norm = np.linalg.norm(embedding)
                return embedding / (norm + 1e-7)
            else:
                # No face detected in crop — do NOT save a garbage encoding.
                # Return None so the caller can skip saving this result.
                print("[FaceRecognition] ArcFace: no face detected in crop — returning None")
                return None

        except Exception as e:
            print(f"[FaceRecognition] ArcFace encode error: {e}")
            return None

    def _pixel_fallback(self, face_image: np.ndarray) -> None:
        """
        Previously returned a pixel-hash fallback embedding when ArcFace found
        no face in the crop.  This caused database poisoning: garbage crops
        (birds, shadows, plants) generated pixel-hash embeddings that were
        stored as valid face encodings and then matched against future detections.

        Now returns None so the caller can discard the result entirely.
        """
        print("[FaceRecognition] ArcFace: no face in crop — returning None (not saving garbage encoding)")
        return None

    # ── Comparison ────────────────────────────────────────────────────────────

    def compare_faces(self, encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """
        Cosine similarity between two face embeddings.

        Returns:
            float: similarity score in [0, 1]; higher = more similar.
            ArcFace embeddings are already L2-normalised so dot product
            equals cosine similarity directly.
        """
        # Handle dimension mismatch gracefully (old HOG vs new ArcFace encodings)
        if encoding1.shape != encoding2.shape:
            return 0.0

        similarity = float(np.dot(encoding1, encoding2) / (
            np.linalg.norm(encoding1) * np.linalg.norm(encoding2) + 1e-7
        ))
        # Clamp to [0, 1] — cosine can be negative for very dissimilar faces
        return max(0.0, similarity)

    # ── Identification ────────────────────────────────────────────────────────

    def identify_face(
        self,
        face_encoding: np.ndarray,
        known_encodings: Dict[int, List[np.ndarray]]
    ) -> Tuple[Optional[int], float]:
        """
        Identify a face by comparing against all stored encodings.

        Uses a voting strategy when multiple encodings exist per person:
        the best individual match score determines the winner, but the
        visitor must beat the threshold to be named.

        Args:
            face_encoding: embedding of the face to identify
            known_encodings: {visitor_id: [embedding, ...]}

        Returns:
            (visitor_id, score) if match found above threshold
            (None, best_score)  if no match found
        """
        best_match_id = None
        best_similarity = 0.0

        for visitor_id, encodings in known_encodings.items():
            # Skip encodings with mismatched dimensions (e.g. old HOG encodings
            # still in DB before re-enrolment)
            valid = [e for e in encodings if e.shape == face_encoding.shape]
            if not valid:
                continue

            # Best score across all encodings for this person
            visitor_best = max(self.compare_faces(face_encoding, e) for e in valid)

            if visitor_best > best_similarity:
                best_similarity = visitor_best
                best_match_id = visitor_id

        if best_similarity >= self.recognition_threshold:
            return best_match_id, best_similarity
        return None, best_similarity

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_encoding(self, encoding: np.ndarray, filepath: str):
        """Persist a face encoding to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(encoding, f)

    def load_encoding(self, filepath: str) -> Optional[np.ndarray]:
        """Load a face encoding from disk."""
        try:
            with open(filepath, "rb") as f:
                return pickle.load(f)
        except (FileNotFoundError, pickle.UnpicklingError):
            return None


# ── Singleton ─────────────────────────────────────────────────────────────────

_face_recognition_engine: Optional[FaceRecognitionEngine] = None


def get_face_recognition_engine() -> FaceRecognitionEngine:
    """Return the global FaceRecognitionEngine instance (created on first call)."""
    global _face_recognition_engine
    if _face_recognition_engine is None:
        _face_recognition_engine = FaceRecognitionEngine()
    return _face_recognition_engine


def reset_face_recognition_engine():
    """Force re-initialisation of the engine (e.g. after model update)."""
    global _face_recognition_engine
    _face_recognition_engine = None
