from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult

class ChatHandler(BaseHandler):
    INTENT_NAME = "CHAT"

    def handle(self, intent, state, permission_manager):
        response = intent.slots.get("response")
        if not response:
            return TaskResult(False, "I didn't have a response.")
            
        return TaskResult(True, message=response)
