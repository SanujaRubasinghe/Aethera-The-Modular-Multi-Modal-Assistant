import threading
import queue
from controllers.task_dispatcher import TaskDispatcher

class PermissionManager:
    def __init__(self, intent_queue, response_queue):
        self.intent = intent_queue
        self.response = response_queue
        self._lock = threading.Lock()
        self._pending = None
        self._event = threading.Event()

    def request(self, permission_request):
        with self._lock:
            self._pending = permission_request
            self._event.clear()

        self.response.put(permission_request.prompt)

        approved = self._event.wait(timeout=permission_request.timeout)

        if not approved:
            return False
        
        return self._pending is None
    
    def resolve(self, intent_name: str):
        with self._lock:
            if not self._pending:
                return False
            
            if intent_name == "CONFIRM_YES":
                self._pending = None
                self._event.set()
                return True
            
            if intent_name == "CONFIRM_NO":
                self._pending = None
                self._event.set()
                return False
            
        return False