from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult

class IntroduceSelfHandler(BaseHandler):
    INTENT_NAME = "INTRODUCE_SELF"

    def handle(self, intent, state, permission_manager):
        introduction = (
            "Hello! I am Aethera, your multi-modal modular assistant. "
            "I'm designed to help you navigate your Windows environment with voice and gestures, "
            "while providing advanced biometric security and local intelligence."
        )
        return TaskResult(True, message=introduction)
