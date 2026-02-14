import threading
import queue
import time
import json
import os
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks import python
import numpy as np
from typing import Optional, Dict, Any
from vision.camera_manager import CameraManager
from vision.gesture_classifier import GestureClassifier
from intent.intent_classifier import Intent
from config.constants import GESTURE_DEBOUNCE_MS

from state.assistant_state import AssistantState

class GestureController(threading.Thread):
    def __init__(self, camera: CameraManager, state: AssistantState, intent_queue: queue.Queue, shutdown_event: threading.Event):
        super().__init__(daemon=True)
        self.camera = camera
        self.state = state
        self.intent_queue = intent_queue
        self.shutdown_event = shutdown_event
        self.classifier = GestureClassifier()
        self.model_path = "./vision/gesture_model/hand_landmarker.task"
        
        # MediaPipe initialization
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.LIVE_STREAM,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
            result_callback=self._internal_callback
        )
        self.hands = vision.HandLandmarker.create_from_options(options)
        
        # Configuration
        self.mappings = self._load_mappings()
        
        # State tracking
        self.last_gesture: Optional[str] = None
        self.gesture_start_time = 0
        self.timestamp = 0
    
    def _internal_callback(self, result, output_image, timestamp_ms):
        if result.hand_landmarks:
            for i, hand_landmarks in enumerate(result.hand_landmarks):
                landmarks = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks], dtype=np.float32)
                
                handedness = "Left" if result.handedness[i][0].category_name == "Right" else "Right"
                gesture = self.classifier.classify_gesture(landmarks, hand_label=handedness)
                
                if gesture:
                    self._handle_gesture(gesture)
                    break # Handle one hand at a time
        else:
            self.last_gesture = None

    def _load_mappings(self) -> Dict[str, Any]:
        mapping_path = "vision/gesture_mappings/gesture_mappings.json"
        if os.path.exists(mapping_path):
            with open(mapping_path, 'r') as f:
                return json.load(f)
        return {}

    def run(self):
        print("GestureController: Thread started")
        with self.state._lock:
            self.state.gesture_control_active = True
        
        while not self.shutdown_event.is_set():
            frame = self.camera.get_latest_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            self._process_gesture(frame)
            time.sleep(0.01)

        with self.state._lock:
            self.state.gesture_control_active = False
        self.hands.close()
        print("GestureController: Thread stopped")

    def _process_gesture(self, frame: np.ndarray):
        self.timestamp += 1
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        self.hands.detect_async(mp_image, self.timestamp)

    def _handle_gesture(self, gesture: str):
        current_time = time.time() * 1000

        if gesture == self.last_gesture:
            duration = current_time - self.gesture_start_time
            if duration >= GESTURE_DEBOUNCE_MS:
                self._dispatch_gesture_intent(gesture)
                self.gesture_start_time = current_time + 1000 
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
