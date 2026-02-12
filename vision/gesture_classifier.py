import numpy as np
from typing import List, Optional, Dict, Any

class GestureClassifier:
    def __init__(self):
        self.history = []
        self.history_len = 10

    def classify_gesture(self, landmarks, prev_landmarks=None) -> Optional[str]:
        """
        Main entry point for gesture classification.
        landmarks: List of 21 (x, y, z) MediaPipe landmarks for one hand.
        """
        if not landmarks:
            return None

        # 1. Basic Finger States (Is it up or down?)
        fingers_up = self._get_fingers_up(landmarks)
        num_fingers = sum(fingers_up)

        # 2. Heuristic Classification
        # assistant Control / Basics
        if num_fingers == 5:
            return "open_palm"
        if num_fingers == 0:
            return "fist"
        
        # Victory (Index + Middle)
        if fingers_up == [0, 1, 1, 0, 0]:
            return "victory"
        
        # Thumbs
        if fingers_up == [1, 0, 0, 0, 0]:
            # Simple check for orientation could distinguish Thumb Up vs Down
            # For now, we assume pose-based or motion-based refinement
            if landmarks[4][1] < landmarks[3][1]: # Thumb tip above joint
                return "thumbs_up"
            else:
                return "thumbs_down"

        # Point (Index only)
        if fingers_up == [0, 1, 0, 0, 0]:
            return "point"

        # OK Sign (Thumb + Index touching, others up)
        if num_fingers == 3 and not fingers_up[1] and not fingers_up[0]:
            # Further refinement: check distance between Thumb tip (4) and Index tip (8)
            dist = self._get_dist(landmarks[4], landmarks[8])
            if dist < 0.05:
                return "ok_sign"

        # L-Shape (Thumb + Index up)
        if fingers_up == [1, 1, 0, 0, 0]:
            return "l_shape"

        # Finger Gun (L-Shape + Middle partially up or specific angle)
        # Simplified: if L-shape but horizontally pointed
        
        # 3. Dynamic Motion Tracking
        if prev_landmarks:
            motion = self._detect_motion(landmarks, prev_landmarks)
            if motion:
                return motion

        return None

    def _get_fingers_up(self, landmarks) -> List[int]:
        """Returns a list of 5 integers (0 or 1) representing thumb to pinky state."""
        fingers = []
        # Thumb: Tip (4) is further from wrist (0) than knuckle (2) horizontally
        # Note: Depending on hand orientation (left/right/palm in/out), this varies.
        # Simple heuristic: x-distance for thumb
        if landmarks[4][0] > landmarks[3][0]: # Simplified
            fingers.append(1)
        else:
            fingers.append(0)

        # Other 4 fingers: Tip y < Pip y (y decreases upwards in MediaPipe)
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        
        for tip, pip in zip(finger_tips, finger_pips):
            if landmarks[tip][1] < landmarks[pip][1]:
                fingers.append(1)
            else:
                fingers.append(0)
        
        return fingers

    def _get_dist(self, p1, p2):
        return np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def _detect_motion(self, current, prev) -> Optional[str]:
        """Detects swipes or rotations based on wrist/center movement."""
        # Wrist is landmark 0
        dx = current[0][0] - prev[0][0]
        dy = current[0][1] - prev[0][1]
        
        threshold = 0.05
        if abs(dx) > threshold:
            return "swipe_right" if dx > 0 else "swipe_left"
        if abs(dy) > threshold:
            return "swipe_down" if dy > 0 else "swipe_up"
            
        return None
