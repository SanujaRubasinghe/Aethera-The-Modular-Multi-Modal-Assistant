import ctypes
import queue

from typing import Optional
from state.assistant_state import AssistantState
from vision.intrusion_logger import IntrusionLogger
from vision.camera_manager import CameraManager
from intent.intent_classifier import Intent
from config.constants import LOCK_ON_UNAUTHORIZED

class SecurityGate:
    def __init__(self, state: AssistantState, camera: CameraManager, response_queue: Optional[queue.Queue] = None):
        self.state = state
        self.camera = camera
        self.response_queue = response_queue
        self.logger = IntrusionLogger()
        self.last_reported_count = 0

    def allow(self, intent: Intent) -> bool:
        # Safety fallback
        if not getattr(self.camera, "available", True):
            return True

        # Always allow if authenticated
        if self.state.is_authenticated:
            self.check_and_report_intrusions()
            return True


        # Exemptions
        if intent.name in ["WAKE_ASSISTANT", "FACE_RECOG_STATUS"]:
            return True

        # Blocked
        print(f"SecurityGate: Blocked intent {intent.name} due to lack of authentication.")
        
        # Log intrusion attempt with photo
        frame = self.camera.get_latest_frame()
        if frame is not None:
            self.logger.log_intrusion(frame)
        else:
            print("SecurityGate: Warning: Could not capture frame for intrusion log.")
        
        self.state.pending_intrusion_report = True
        
        # Handle OS lock if enabled
        if LOCK_ON_UNAUTHORIZED:
            self.lock_workstation()

        return False

    def check_and_report_intrusions(self):
        if self.state.pending_intrusion_report:
            count = self.logger.get_unreviewed_count()
            print(f"SecurityGate: Found {count} unreviewed intrusion attempts.")
            if count > 0:
                msg = f"Security Alert: There were {count} intrusion attempts while you were away."
                print(f"SecurityGate: {msg}")
                if self.response_queue:
                    self.response_queue.put(msg)
                
            # Clear pending report status
            self.state.pending_intrusion_report = False
            self.logger.mark_all_reviewed()

    def lock_workstation(self):
        """Platform dependent lock."""
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            print(f"SecurityGate: Failed to lock workstation: {e}")

