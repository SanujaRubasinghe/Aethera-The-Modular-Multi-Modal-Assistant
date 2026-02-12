import threading
import queue
import time
import json
import os
import cv2
import mediapipe as mp
from typing import Optional, Dict, Any
from vision.camera_manager import CameraManager
from vision.gesture_classifier import GestureClassifier
from intent.intent_classifier import Intent
from config.constants import GESTURE_DEBOUNCE_MS

class GestureController:
    def __init__(self, camera: CameraManager, intent_queue: queue.Queue, shutdown_event: threading.Event):
        self.camera = camera
        self.intent_queue = intent_queue
        self.shutdown_event = shutdown_event
        self.classifier = GestureClassifier()
        
        # MediaPipe initialization
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Configuration
        self.mappings = self._load_mappings()
        
        # State tracking
        self.last_gesture: Optional[str] = None
        self.gesture_start_time = 0
        self.prev_landmarks = None

    def _load_mappings(self) -> Dict[str, Any]:
        mapping_path = "config/gesture_mappings.json"
        if os.path.exists(mapping_path):
            with open(mapping_path, 'r') as f:
                return json.load(f)
        return {}

    def start(self):
        """Starts the gesture detection callback on the camera manager."""
        self.camera.register_consumer(self.process_frame)
        print("GestureController: Started")

    def stop(self):
        self.camera.unregister_consumer(self.process_frame)
        self.hands.close()
        print("GestureController: Stopped")

    def process_frame(self, frame):
        """Callback from CameraManager."""
        if self.shutdown_event.is_set():
            return

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Convert landmarks to list of (x,y,z)
                landmarks = [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark]
                
                # Classify
                gesture = self.classifier.classify_gesture(landmarks, self.prev_landmarks)
                self.prev_landmarks = landmarks
                
                if gesture:
                    self._handle_gesture(gesture)
                    break # Handle one hand at a time for now
        else:
            self.last_gesture = None
            self.prev_landmarks = None

    def _handle_gesture(self, gesture: str):
        """Debounce and dispatch intents."""
        current_time = time.time() * 1000

        if gesture == self.last_gesture:
            duration = current_time - self.gesture_start_time
            if duration >= GESTURE_DEBOUNCE_MS:
                self._dispatch_gesture_intent(gesture)
                # Reset start time to avoid rapid repeated firing for static gestures
                # unless specified otherwise in mapping (e.g. continuous mode)
                self.gesture_start_time = current_time + 1000 # 1s cooldown
        else:
            self.last_gesture = gesture
            self.gesture_start_time = current_time

    def _dispatch_gesture_intent(self, gesture: str):
        mapping = self.mappings.get(gesture)
        if not mapping:
            return

        intent_name = mapping.get("intent")
        slots = mapping.get("slots", {})
        
        print(f"GestureController: Detected {gesture} -> Intent: {intent_name}")
        
        intent = Intent(name=intent_name, slots=slots)
        self.intent_queue.put(intent)
