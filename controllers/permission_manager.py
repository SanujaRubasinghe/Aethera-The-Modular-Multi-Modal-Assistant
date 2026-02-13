import threading
import queue
import time

class PermissionManager:
    def __init__(self, intent_queue, response_queue, wake_event):
        self.intent_queue = intent_queue
        self.response_queue = response_queue
        self.wake_event = wake_event
        self._lock = threading.Lock()
        self._pending = None

    def request(self, permission_request):
        print(f"[PermissionManager] Requesting: {permission_request.prompt}")
        
        # Send prompt to TTS
        self.response_queue.put(permission_request.prompt)
        
        # Trigger STT to listen for response
        self.wake_event.set()

        start_time = time.time()
        timeout = permission_request.timeout

        while time.time() - start_time < timeout:
            try:
                intent = self.intent_queue.get(timeout=1.0)
                
                print(f"[PermissionManager] Received intent: {intent.name}")

                if intent.name == "CONFIRM_YES":
                    return True
                
                if intent.name == "CONFIRM_NO":
                    return False
                
                print(f"[PermissionManager] Unexpected intent {intent.name}, putting back in queue.")
                self.intent_queue.put(intent)
                return False
                
            except queue.Empty:
                continue

        print("[PermissionManager] Request timed out")
        return False