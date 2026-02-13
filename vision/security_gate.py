import ctypes
from typing import Optional
from state.assistant_state import AssistantState
from vision.intrusion_logger import IntrusionLogger
from vision.camera_manager import CameraManager
from intent.intent_classifier import Intent
from config.constants import LOCK_ON_UNAUTHORIZED

class SecurityGate:
    def __init__(self, state: AssistantState, camera: CameraManager):
        self.state = state
        self.camera = camera
        self.logger = IntrusionLogger()
        self.last_reported_count = 0

    def allow(self, intent: Intent) -> bool:
        """
        Verdict on whether to allow the intent.
        Exempts certain intents like 'WAKE_ASSISTANT' which might be needed for auth.
        Always allows if the camera is not available to avoid locking out the user.
        """
        # Safety fallback
        if not getattr(self.camera, "available", True):
            return True

        # Always allow if authenticated
        if self.state.is_authenticated:
            # Check if we should report previous intrusions
            self._check_and_report_intrusions()
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
            self.state.pending_intrusion_report = True
        
        # Handle OS lock if enabled
        if LOCK_ON_UNAUTHORIZED:
            self._lock_workstation()

        return False

    def _check_and_report_intrusions(self):
        """Called when owner returns."""
        if self.state.pending_intrusion_report:
            count = self.logger.get_unreviewed_count()
            if count > 0:
                # This flag will be picked up by the GUI/Assistant to notify the user
                # We could also directly queue a response here, but better to keep it decoupled.
                pass

    def _lock_workstation(self):
        """Platform dependent lock."""
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            print(f"SecurityGate: Failed to lock workstation: {e}")
