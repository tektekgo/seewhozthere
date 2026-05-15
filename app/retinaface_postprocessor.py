"""
RetinaFace Post-Processor for Hailo AI HAT+

This module implements the complete post-processing pipeline for RetinaFace face detection.
It converts raw Hailo output tensors into usable face bounding boxes.

EDUCATIONAL GUIDE:
==================

What is Post-Processing?
------------------------
After the Hailo chip runs the neural network (inference), it outputs RAW NUMBERS (tensors).
Post-processing converts these numbers into meaningful information (face boxes, confidence scores).

Think of it like this:
- Hailo Chip = A super-fast calculator
- Post-Processing = Reading the answer and understanding what it means

The Pipeline:
-------------
1. INFERENCE (Hailo chip) → Raw output tensors [FAST - 10ms]
2. DEQUANTIZATION → Convert UINT8 to float values [FAST - 1ms]
3. ANCHOR DECODING → Map predictions to image coordinates [FAST - 2ms]
4. CONFIDENCE FILTERING → Keep only high-confidence detections [FAST - 1ms]
5. NMS (Non-Maximum Suppression) → Remove duplicate boxes [FAST - 2ms]

Total post-processing time: ~6ms
Total pipeline time: ~16ms = 62 FPS!

Key Concepts:
-------------
- **Tensor**: A multi-dimensional array of numbers (like a spreadsheet with many sheets)
- **Anchor**: A pre-defined box at a specific location and size
- **NMS**: Removes overlapping boxes (keeps the best one)
- **Confidence**: How sure the model is that it found a face (0.0 to 1.0)
"""

import numpy as np
import cv2
from typing import List, Tuple, Dict
import time


class RetinaFacePostProcessor:
    """
    Complete post-processor for RetinaFace face detection model.
    
    This class handles all the complex math needed to convert Hailo's
    raw output tensors into face bounding boxes.
    """
    
    def __init__(self, 
                 input_width: int = 1280,
                 input_height: int = 736,
                 confidence_threshold: float = 0.6,
                 nms_threshold: float = 0.4):
        """
        Initialize the post-processor.
        
        Args:
            input_width: Model input width (RetinaFace uses 1280)
            input_height: Model input height (RetinaFace uses 736)
            confidence_threshold: Minimum confidence to keep a detection (0.0-1.0)
            nms_threshold: IoU threshold for NMS (lower = more aggressive filtering)
        
        LEARNING NOTE:
        - Confidence threshold: If model is 60% sure it's a face, keep it
        - NMS threshold: If two boxes overlap by more than 40%, keep only the best one
        """
        self.input_width = input_width
        self.input_height = input_height
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        
        # RetinaFace configuration for anchor generation
        # These are the "grid sizes" the model uses to detect faces at different scales
        self.cfg = {
            'min_sizes': [[16, 32], [64, 128], [256, 512]],  # Small, medium, large faces
            'steps': [8, 16, 32],  # How far apart anchors are placed
            'variance': [0.1, 0.2]  # Scaling factors for decoding
        }
        
        # Generate anchors (pre-defined boxes)
        # This is done once at initialization for speed
        self.priors = self._generate_priors()
        
        print(f"[RetinaFacePostProcessor] Initialized")
        print(f"[RetinaFacePostProcessor] Input size: {input_width}x{input_height}")
        print(f"[RetinaFacePostProcessor] Generated {len(self.priors)} anchor boxes")
        print(f"[RetinaFacePostProcessor] Confidence threshold: {confidence_threshold}")
    
    def _generate_priors(self) -> np.ndarray:
        """
        Generate anchor boxes (priors) for the RetinaFace model.
        
        WHAT ARE ANCHORS?
        -----------------
        Anchors are pre-defined boxes placed all over the image at different:
        - Positions (every 8, 16, or 32 pixels)
        - Sizes (16x16, 32x32, 64x64, etc.)
        
        WHY USE ANCHORS?
        ----------------
        Instead of predicting absolute coordinates, the model predicts:
        "How much to adjust this anchor box to fit the face"
        
        This makes learning easier and more accurate!
        
        ANALOGY:
        --------
        Imagine you're trying to find a person in a crowd:
        - Anchors = Grid of searchlights at different heights
        - Model = Adjusts each searchlight to point at faces
        - Post-processing = Reads which searchlights found faces
        
        Returns:
            Array of anchor boxes, shape (num_anchors, 4)
            Each anchor: [center_x, center_y, width, height] (normalized 0-1)
        """
        anchors = []
        
        # For each scale (small, medium, large faces)
        for k, step in enumerate(self.cfg['steps']):
            # Calculate feature map size
            # Example: 1280 / 8 = 160 columns, 736 / 8 = 92 rows
            feature_width = self.input_width // step
            feature_height = self.input_height // step
            
            min_sizes = self.cfg['min_sizes'][k]
            
            # Place anchors at each grid position
            for i in range(feature_height):
                for j in range(feature_width):
                    for min_size in min_sizes:
                        # Calculate anchor center (normalized 0-1)
                        cx = (j + 0.5) * step / self.input_width
                        cy = (i + 0.5) * step / self.input_height
                        
                        # Calculate anchor size (normalized 0-1)
                        s_kx = min_size / self.input_width
                        s_ky = min_size / self.input_height
                        
                        anchors.append([cx, cy, s_kx, s_ky])
        
        return np.array(anchors, dtype=np.float32)
    
    def _decode_boxes(self, 
                      loc: np.ndarray, 
                      priors: np.ndarray, 
                      variances: List[float]) -> np.ndarray:
        """
        Decode bounding box predictions.
        
        WHAT IS DECODING?
        -----------------
        The model outputs OFFSETS (adjustments) to anchor boxes, not absolute coordinates.
        Decoding converts these offsets into actual pixel coordinates.
        
        MATH EXPLANATION:
        -----------------
        Model outputs: [dx, dy, dw, dh] for each anchor
        - dx, dy: How much to move the box center
        - dw, dh: How much to scale the box size
        
        Decoding formula:
        - box_center_x = anchor_center_x + (dx * variance[0] * anchor_width)
        - box_center_y = anchor_center_y + (dy * variance[0] * anchor_height)
        - box_width = anchor_width * exp(dw * variance[1])
        - box_height = anchor_height * exp(dh * variance[1])
        
        Args:
            loc: Location predictions from model, shape (num_anchors, 4)
            priors: Anchor boxes, shape (num_anchors, 4)
            variances: Scaling factors [0.1, 0.2]
        
        Returns:
            Decoded boxes in format [x1, y1, x2, y2] (top-left, bottom-right)
        """
        # Decode box centers
        boxes = np.concatenate((
            priors[:, :2] + loc[:, :2] * variances[0] * priors[:, 2:],  # Center (x, y)
            priors[:, 2:] * np.exp(loc[:, 2:] * variances[1])  # Size (w, h)
        ), axis=1)
        
        # Convert from [cx, cy, w, h] to [x1, y1, x2, y2]
        boxes[:, :2] -= boxes[:, 2:] / 2  # Top-left corner
        boxes[:, 2:] += boxes[:, :2]  # Bottom-right corner
        
        return boxes
    
    def _decode_landmarks(self,
                         landms: np.ndarray,
                         priors: np.ndarray,
                         variances: List[float]) -> np.ndarray:
        """
        Decode facial landmark predictions.
        
        WHAT ARE LANDMARKS?
        -------------------
        Landmarks are key points on a face:
        - Left eye, right eye
        - Nose tip
        - Left mouth corner, right mouth corner
        
        Total: 5 landmarks = 10 coordinates (x, y for each)
        
        WHY LANDMARKS?
        --------------
        - Face alignment (straighten tilted faces)
        - Face recognition (normalize face orientation)
        - Emotion detection (mouth/eye positions)
        
        Args:
            landms: Landmark predictions, shape (num_anchors, 10)
            priors: Anchor boxes, shape (num_anchors, 4)
            variances: Scaling factors
        
        Returns:
            Decoded landmarks, shape (num_anchors, 10)
        """
        landmarks = np.concatenate((
            priors[:, :2] + landms[:, 0:2] * variances[0] * priors[:, 2:],  # Left eye
            priors[:, :2] + landms[:, 2:4] * variances[0] * priors[:, 2:],  # Right eye
            priors[:, :2] + landms[:, 4:6] * variances[0] * priors[:, 2:],  # Nose
            priors[:, :2] + landms[:, 6:8] * variances[0] * priors[:, 2:],  # Left mouth
            priors[:, :2] + landms[:, 8:10] * variances[0] * priors[:, 2:]  # Right mouth
        ), axis=1)
        
        return landmarks
    
    def _nms(self, 
             boxes: np.ndarray, 
             scores: np.ndarray, 
             threshold: float) -> List[int]:
        """
        Non-Maximum Suppression (NMS) - Remove duplicate detections.
        
        WHAT IS NMS?
        ------------
        When detecting faces, the model often finds the SAME face multiple times
        (from different anchors). NMS keeps only the BEST detection.
        
        HOW IT WORKS:
        -------------
        1. Sort all detections by confidence (highest first)
        2. Take the best detection, keep it
        3. Remove all other detections that overlap with it too much
        4. Repeat until no detections left
        
        WHAT IS IoU (Intersection over Union)?
        ---------------------------------------
        Measures how much two boxes overlap:
        - IoU = (Area of Overlap) / (Area of Union)
        - IoU = 0.0: No overlap
        - IoU = 1.0: Perfect overlap (same box)
        
        Example:
        - Box A: [10, 10, 50, 50]
        - Box B: [15, 15, 55, 55]
        - These boxes overlap a lot! NMS will keep only the one with higher confidence.
        
        Args:
            boxes: Bounding boxes, shape (N, 4) in format [x1, y1, x2, y2]
            scores: Confidence scores, shape (N,)
            threshold: IoU threshold (0.4 = remove boxes with >40% overlap)
        
        Returns:
            List of indices to keep
        """
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        # Calculate area of each box
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        
        # Sort by confidence score (highest first)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            # Keep the box with highest confidence
            i = order[0]
            keep.append(i)
            
            # Calculate IoU with all other boxes
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            # Calculate intersection area
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            
            # Calculate IoU
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            
            # Keep only boxes with IoU below threshold
            inds = np.where(iou <= threshold)[0]
            order = order[inds + 1]
        
        return keep
    
    def process(self, 
                output_tensors: List[np.ndarray],
                original_shape: Tuple[int, int]) -> List[Dict]:
        """
        Complete post-processing pipeline.
        
        PIPELINE OVERVIEW:
        ------------------
        1. Parse output tensors (9 tensors → 3 types)
        2. Apply softmax to confidence scores
        3. Decode bounding boxes and landmarks
        4. Scale to original image size
        5. Filter by confidence threshold
        6. Apply NMS to remove duplicates
        
        Args:
            output_tensors: List of 9 output tensors from Hailo
                - Tensors 0, 3, 6: Bounding boxes (4 values each)
                - Tensors 1, 4, 7: Confidence scores (2 values: background, face)
                - Tensors 2, 5, 8: Landmarks (10 values: 5 points x 2 coords)
            original_shape: (height, width) of original frame
        
        Returns:
            List of detections, each containing:
            - bbox: [x, y, w, h] in original image coordinates
            - confidence: float (0.0-1.0)
            - landmarks: [[x1,y1], [x2,y2], ...] (5 points)
        """
        start_time = time.time()
        
        # Step 1: Parse and concatenate tensors by type
        # RetinaFace outputs 3 feature maps (scales), each with bbox/conf/landmarks
        loc_list = []  # Bounding box offsets
        conf_list = []  # Confidence scores
        landms_list = []  # Facial landmarks
        
        for i in range(0, len(output_tensors), 3):
            loc_list.append(output_tensors[i].reshape(-1, 4))
            conf_list.append(output_tensors[i+1].reshape(-1, 2))
            landms_list.append(output_tensors[i+2].reshape(-1, 10))
        
        loc = np.concatenate(loc_list, axis=0)
        conf = np.concatenate(conf_list, axis=0)
        landms = np.concatenate(landms_list, axis=0)
        
        print(f"[PostProcessor] Parsed tensors: loc={loc.shape}, conf={conf.shape}, landms={landms.shape}")
        # Diagnostic: show raw conf range
        _raw_c1_max = float(conf[:, 1].max())
        _raw_c1_min = float(conf[:, 1].min())
        print(f"[PostProcessor] Raw conf[:,1] (face class) — min={_raw_c1_min:.3f}, max={_raw_c1_max:.3f}")
        
        # Step 2: Apply softmax to confidence scores (numerically stable version)
        # Subtract row-max before exp to prevent overflow (inf/inf = nan bug)
        # The Hailo RetinaFace model outputs [background, face] — class 1 is FACE
        # class 0 (background) has high logits everywhere; class 1 (face) is only
        # high when a real face is present — so we must use conf[:,1] as the score
        conf_stable = conf - conf.max(axis=1, keepdims=True)
        exp_conf = np.exp(conf_stable)
        scores = exp_conf[:, 1] / exp_conf.sum(axis=1)
        print(f"[PostProcessor] Softmax face scores — max={float(scores.max()):.4f}, threshold={self.confidence_threshold}")
        
        # Step 3: Decode bounding boxes and landmarks
        boxes = self._decode_boxes(loc, self.priors, self.cfg['variance'])
        landmarks = self._decode_landmarks(landms, self.priors, self.cfg['variance'])
        
        # Step 4: Scale to original image size
        original_height, original_width = original_shape
        scale = np.array([original_width, original_height, original_width, original_height])
        boxes = boxes * scale
        
        scale_landmarks = np.array([original_width, original_height] * 5)
        landmarks = landmarks * scale_landmarks
        
        # Step 5: Filter by confidence threshold
        inds = np.where(scores > self.confidence_threshold)[0]
        boxes = boxes[inds]
        landmarks = landmarks[inds]
        scores = scores[inds]
        
        _score_max = float(scores.max()) if len(scores) > 0 else 0.0
        print(f"[PostProcessor] After filter — max={_score_max:.4f}, threshold={self.confidence_threshold}")
        print(f"[PostProcessor] After confidence filter: {len(boxes)} detections")
        
        # Step 5b: Filter by face shape — reject non-face shaped detections
        # Faces are roughly square (aspect ratio 0.55–1.6) and bounded in size.
        # Tighter than the theoretical range to reject real-world false positives:
        #   - Birds/animals cluster into wide-short bboxes (ratio < 0.55)
        #   - Landscape objects (cars, pots, signs) produce wide bboxes (ratio > 1.6)
        # Minimum size 35×35px: anything smaller is too distant/blurry for ArcFace.
        # Maximum size 350×350px: anything larger is not a face at doorbell distance.
        if len(boxes) > 0:
            widths  = boxes[:, 2] - boxes[:, 0]
            heights = boxes[:, 3] - boxes[:, 1]
            # Avoid division by zero
            heights_safe = np.where(heights > 0, heights, 1)
            aspect_ratios = widths / heights_safe
            min_face_px = 35   # below this, ArcFace embedding quality is too poor
            max_face_px = 350  # above this, not a face at normal doorbell distance
            shape_mask = (
                (aspect_ratios >= 0.55) &  # not too wide/short (bird clusters, landscape)
                (aspect_ratios <= 1.6)  &  # not too narrow/tall (vertical signs, slivers)
                (widths  >= min_face_px) &
                (heights >= min_face_px) &
                (widths  <= max_face_px) &
                (heights <= max_face_px)
            )
            rejected = int((~shape_mask).sum())
            if rejected > 0:
                print(f"[PostProcessor] Shape filter rejected {rejected} non-face bbox(es) (aspect/size)")
            boxes     = boxes[shape_mask]
            landmarks = landmarks[shape_mask]
            scores    = scores[shape_mask]
        
        print(f"[PostProcessor] After shape filter: {len(boxes)} detections")
        
        # Step 6: Apply NMS
        keep = self._nms(boxes, scores, self.nms_threshold)
        boxes = boxes[keep]
        landmarks = landmarks[keep]
        scores = scores[keep]
        
        elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"[PostProcessor] After NMS: {len(boxes)} detections")
        print(f"[PostProcessor] Post-processing time: {elapsed:.1f}ms")
        
        # Step 7: Format results
        detections = []
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes[i]
            detection = {
                'bbox': (int(x1), int(y1), int(x2 - x1), int(y2 - y1)),  # (x, y, w, h)
                'confidence': float(scores[i]),
                'landmarks': landmarks[i].reshape(5, 2).tolist()  # 5 points, each (x, y)
            }
            detections.append(detection)
        
        return detections
