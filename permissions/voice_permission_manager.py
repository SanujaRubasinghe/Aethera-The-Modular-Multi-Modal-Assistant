import queue
import threading
from permissions.permission_request import PermissionRequest

class VoicePermissionManager:
    def __init__(self, response_queue, intent_queue):
        self.response_queue = response_queue
        self.intent_queue = intent_queue
        self.pending_request = None
        self._lock = threading.Lock()

    def request(self, permission: PermissionRequest):
        with self._lock:
            self.pending_request = permission

        self.response_queue.put(permission.prompt)

    def handle_intent(self, intent):
        if not self.pending_request:
            return False
        
        answer = intent.name.lower()

        with self._lock:
            permission = self.pending_request
            self.pending_request = None

        if answer in ("yes", "confirm", "ok", "sure"):
            permission.on_approve()
        else:
            permission.on_deny()

        return True