import cv2
import threading
import time
import numpy as np
from typing import List, Callable, Optional
from config.constants import CAMERA_FPS

class CameraManager(threading.Thread):
    def __init__(self, shutdown_event: threading.Event, source: int = 0):
        super().__init__(daemon=True)
        self.shutdown_event = shutdown_event
        self.source = source
        self.frame_callbacks: List[Callable[[np.ndarray], None]] = []
        self._lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_delay = 1.0 / CAMERA_FPS

    def register_consumer(self, callback: Callable[[np.ndarray], None]):
        """Register a callback function to receive camera frames."""
        with self._lock:
            if callback not in self.frame_callbacks:
                self.frame_callbacks.append(callback)

    def unregister_consumer(self, callback: Callable[[np.ndarray], None]):
        """Unregister a callback function."""
        with self._lock:
            if callback in self.frame_callbacks:
                self.frame_callbacks.remove(callback)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame captured."""
        with self._lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def run(self):
        print(f"CameraManager: Starting capture on source {self.source}")
        cap = cv2.VideoCapture(self.source)
        
        if not cap.isOpened():
            print("CameraManager: Failed to open camera.")
            return

        while not self.shutdown_event.is_set():
            start_time = time.time()
            
            ret, frame = cap.read()
            if ret:
                # Mirror the frame immediately (most webcams need this for natural interaction)
                frame = cv2.flip(frame, 1)
                
                with self._lock:
                    self.latest_frame = frame
                
                # Notify consumers
                # Create a snapshot of callbacks to avoid locking during execution
                with self._lock:
                    callbacks = list(self.frame_callbacks)
                
                for cb in callbacks:
                    try:
                        cb(frame)
                    except Exception as e:
                        print(f"CameraManager: Error in consumer callback: {e}")
            else:
                print("CameraManager: Failed to read frame.")
                time.sleep(0.5) # Wait a bit before retrying
                continue

            # Maintain FPS cap
            execution_time = time.time() - start_time
            sleep_time = max(0, self.frame_delay - execution_time)
            time.sleep(sleep_time)

        cap.release()
        print("CameraManager: Stopped.")
