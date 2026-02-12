import face_recognition
import cv2
import numpy as np
import os
import pickle
import threading
import time
import queue
from typing import List, Optional
from vision.camera_manager import CameraManager
from state.assistant_state import AssistantState
from config.constants import (
    FACE_DATA_PATH, 
    FACE_MATCH_THRESHOLD, 
    FACE_RECOGNITION_INTERVAL,
    AUTH_TIMEOUT_SECONDS
)

class FaceRecognizer:
    def __init__(self, camera: CameraManager, state: AssistantState, response_queue: queue.Queue, shutdown_event: threading.Event):
        self.camera = camera
        self.state = state
        self.response_queue = response_queue
        self.shutdown_event = shutdown_event
        
        self.known_encodings = []
        self._load_known_faces()
        
        self.last_check_time = 0
        self.last_auth_time = 0
        self._lock = threading.Lock()

    def _load_known_faces(self):
        if os.path.exists(FACE_DATA_PATH):
            try:
                with open(FACE_DATA_PATH, 'rb') as f:
                    self.known_encodings = pickle.load(f)
                print(f"FaceRecognizer: Loaded {len(self.known_encodings)} face encodings.")
            except Exception as e:
                print(f"FaceRecognizer: Error loading face data: {e}")

    def enroll_owner(self, frames: List[np.ndarray]):
        """Compute encodings for owner from multiple frames and save."""
        new_encodings = []
        for frame in frames:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_frame)
            if encodings:
                new_encodings.append(encodings[0])
        
        if new_encodings:
            with self._lock:
                self.known_encodings = new_encodings
                with open(FACE_DATA_PATH, 'wb') as f:
                    pickle.dump(self.known_encodings, f)
            print("FaceRecognizer: Owner enrolled successfully.")
            return True
        return False

    def start(self):
        self.camera.register_consumer(self.process_frame)
        print("FaceRecognizer: Started")

    def stop(self):
        self.camera.unregister_consumer(self.process_frame)
        print("FaceRecognizer: Stopped")

    def process_frame(self, frame):
        if self.shutdown_event.is_set():
            return

        current_time = time.time()
        if current_time - self.last_check_time < FACE_RECOGNITION_INTERVAL:
            return

        self.last_check_time = current_time

        # Run recognition in a separate thread if it's too slow, 
        # but here we rely on the CameraManager's consumer pattern.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Scale down for faster processing
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
        
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)

        matched = False
        if not self.known_encodings:
            # If no owner enrolled, we don't block for now (default to authorized)
            # or we could force enrollment. Plan says enroll via GUI.
            with self.state._lock:
                self.state.is_authenticated = True
            return

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=FACE_MATCH_THRESHOLD)
            if True in matches:
                matched = True
                break
        
        with self.state._lock:
            if matched:
                if not self.state.is_authenticated:
                    print("FaceRecognizer: Owner recognized!")
                    self.response_queue.put("Welcome back, Sanuja.")
                self.state.is_authenticated = True
                self.last_auth_time = current_time
            else:
                # Check for timeout
                if self.state.is_authenticated and (current_time - self.last_auth_time > AUTH_TIMEOUT_SECONDS):
                    print("FaceRecognizer: Authentication timed out.")
                    self.state.is_authenticated = False
                    self.response_queue.put("Access locked. Face not recognized.")
