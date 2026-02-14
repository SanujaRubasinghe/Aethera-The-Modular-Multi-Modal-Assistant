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
        self.available = False
        self.ready_event = threading.Event()

    def register_consumer(self, callback: Callable[[np.ndarray], None]):
        with self._lock:
            if callback not in self.frame_callbacks:
                self.frame_callbacks.append(callback)

    def unregister_consumer(self, callback: Callable[[np.ndarray], None]):
        with self._lock:
            if callback in self.frame_callbacks:
                self.frame_callbacks.remove(callback)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def run(self):
        print(f"CameraManager: Starting capture on source {self.source}")
        
        backends = [
            ("Default", None),
            ("DSHOW", cv2.CAP_DSHOW),
            ("MSMF", cv2.CAP_MSMF),
        ]
        
        cap = None
        for name, backend in backends:
            print(f"CameraManager: Trying backend {name}...")
            if backend is None:
                cap = cv2.VideoCapture(self.source)
            else:
                cap = cv2.VideoCapture(self.source, backend)
            
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"CameraManager: Successfully opened camera with {name} backend.")
                    break
                else:
                    print(f"CameraManager: {name} backend opened but failed to read frame.")
                    cap.release()
                    cap = None
            else:
                print(f"CameraManager: {name} backend failed to open.")
                cap.release()
                cap = None

        if cap is None or not cap.isOpened():
            print("CameraManager: Failed to open camera with all attempted backends.")
            self.available = False
            self.ready_event.set()
            print("CameraManager [STOPPED]")
            return

        self.available = True
        self.ready_event.set()

        while not self.shutdown_event.is_set():
            start_time = time.time()
            
            ret, frame = cap.read()
            if ret:
                # Mirror the frame 
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
