from os_control.win32_monitors import get_connected_monitors
import requests

class TaskResult:
    def __init__(self, success: bool, message: str, data=None):
        self.success = success
        self.message = message
        self.data = data

class TaskDispatcher:
    def __init__(self, assistant_state, permission_manager):
        self.handlers = {}
        self.current_task = None
        self.state = assistant_state
        self.permission_manager = permission_manager

        self.state.monitors.update(get_connected_monitors())

    def register(self, intent_name, handler):
        self.handlers[intent_name] = handler

    def dispatch(self, intent, response_queue):
        handler = self.handlers.get(intent.name)
        if not handler:
            return TaskResult(False, "Sorry, I don't know how to do that.")
        
        self.current_task = handler
        try:
            self.state.update_intent(intent.name)
            return handler.handle(intent, self.state, self.permission_manager)
        finally:
            self.current_task = None

    @staticmethod
    def generate_initial_response(intent):
        # Deprecated: n8n is now handled via N8NHandler
        return None

    # def cancel_current_task(self):
    #     if hasattr(self.current_task, "CANCEL"):
    #         self.current_task.cancel()

