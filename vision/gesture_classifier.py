import numpy as np
from typing import List, Optional

class GestureClassifier:
    def __init__(self, history_len: int = 8):
        self.history = []
        self.history_len = history_len
        self.stable_counter = 0
        self.prev_static = None
        self.required_stable_frames = 3

    def classify_gesture(self, landmarks, hand_label="Right") -> Optional[str]:
        if landmarks is None:
            return None

        motion = self._detect_motion(landmarks)
        if motion:
            return motion

        fingers_up = self._get_fingers_up(landmarks, hand_label)
        num_fingers = sum(fingers_up)

        gesture = None

        if fingers_up == [0, 1, 1, 0, 0]:
            gesture = "victory"

        elif fingers_up == [1, 1, 0, 0, 0]:
            gesture = "l_shape"

        elif fingers_up == [1, 0, 0, 0, 0]:
            gesture = self._detect_thumb_direction(landmarks)

        elif fingers_up == [0, 1, 0, 0, 0]:
            gesture = "point"

        elif self._is_ok_sign(landmarks, fingers_up):
            gesture = "ok_sign"

        elif num_fingers == 5:
            gesture = "open_palm"

        elif num_fingers == 0:
            gesture = "fist"

        return self._temporal_filter(gesture)

    def _get_fingers_up(self, landmarks, hand_label) -> List[int]:
        fingers = []

        if hand_label == "Right":
            thumb_up = landmarks[4][0] > landmarks[3][0]
        else:
            thumb_up = landmarks[4][0] < landmarks[3][0]

        fingers.append(int(thumb_up))

        finger_sets = [
            (5, 6, 8),   # Index
            (9, 10, 12), # Middle
            (13, 14, 16),# Ring
            (17, 18, 20) # Pinky
        ]

        for mcp, pip, tip in finger_sets:
            fingers.append(int(self._is_finger_straight(
                landmarks[mcp],
                landmarks[pip],
                landmarks[tip]
            )))

        return fingers

    def _is_finger_straight(self, mcp, pip, tip) -> bool:
        v1 = np.array(mcp) - np.array(pip)
        v2 = np.array(tip) - np.array(pip)

        cos_angle = np.dot(v1, v2) / (
            np.linalg.norm(v1) * np.linalg.norm(v2)
        )
        angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))

        return angle > 160  # nearly straight


    def _detect_thumb_direction(self, landmarks) -> str:
        return "thumbs_up" if landmarks[4][1] < landmarks[3][1] else "thumbs_down"

    def _is_ok_sign(self, landmarks, fingers_up) -> bool:
        if fingers_up[1] == 0 and fingers_up[0] == 0:
            dist = self._distance(landmarks[4], landmarks[8])

            scale = self._distance(landmarks[0], landmarks[9])
            return bool((dist / scale) < 0.25)
        return False

    def _detect_motion(self, landmarks) -> Optional[str]:
        wrist = landmarks[0]
        self.history.append(wrist)

        if len(self.history) > self.history_len:
            self.history.pop(0)

        if len(self.history) < self.history_len:
            return None

        start = self.history[0]
        end = self.history[-1]

        dx = end[0] - start[0]
        dy = end[1] - start[1]

        threshold = 0.08

        if abs(dx) > threshold:
            return "swipe_right" if dx > 0 else "swipe_left"

        if abs(dy) > threshold:
            return "swipe_down" if dy > 0 else "swipe_up"

        return None

    def _distance(self, p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def _temporal_filter(self, gesture):
        if gesture == self.prev_static:
            self.stable_counter += 1
        else:
            self.stable_counter = 0

        self.prev_static = gesture

        if self.stable_counter >= self.required_stable_frames:
            return gesture

        return None