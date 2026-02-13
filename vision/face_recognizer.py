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

class FaceRecognizer(threading.Thread):
    def __init__(self, camera: CameraManager, state: AssistantState, response_queue: queue.Queue, shutdown_event: threading.Event):
        super().__init__(daemon=True)
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
                self.known_encodings = list(new_encodings)
                with open(FACE_DATA_PATH, 'wb') as f:
                    pickle.dump(self.known_encodings, f)
            print("FaceRecognizer: Owner enrolled successfully.")
            return True
        return False

    def run(self):
        print("FaceRecognizer: Thread started")
        with self.state._lock:
            self.state.face_detection_active = True
        
        while not self.shutdown_event.is_set():
            current_time = time.time()
            if current_time - self.last_check_time < FACE_RECOGNITION_INTERVAL:
                time.sleep(0.1)
                continue

            frame = self.camera.get_latest_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            self.last_check_time = current_time
            self._process_recognition(frame, current_time)

        with self.state._lock:
            self.state.face_detection_active = False
        print("FaceRecognizer: Thread stopped")

    def _process_recognition(self, frame: np.ndarray, current_time: float):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Scale down for faster processing (0.5 is a better balance than 0.25)
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
        
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)

        matched = False
        if not self.known_encodings:
            # If no owner enrolled, default to authenticated to avoid locking the user out
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
                # Check for timeout if no match found (either stranger or no face)
                if self.state.is_authenticated:
                    if current_time - self.last_auth_time > AUTH_TIMEOUT_SECONDS:
                        print("FaceRecognizer: Authentication timed out.")
                        self.state.is_authenticated = False
                        self.response_queue.put("Access locked. Face not recognized.")
