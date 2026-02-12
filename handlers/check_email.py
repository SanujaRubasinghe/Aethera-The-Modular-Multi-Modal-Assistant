from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from config.constants import N8N_WEBHOOK_URL
from state.assistant_state import AssistantState

import requests

class CheckEmailHandler(BaseHandler):
    INTENT_NAME = "CHECK_EMAIL"

    def handle(self, intent, state: AssistantState, permission_manager):
        try:
            payload = {
                "intent_name": self.INTENT_NAME,
                "data": ""
            }

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers)
            all_data = response.json()
            message = all_data.get("message")
            return TaskResult(True, message.get("content", "Sorry there was an error retrieving the e-mail information."))
        except Exception:
            return TaskResult(False, "Sorry, there was an unknown error. I suggest checking the n8n workflows to make sure every thing is working correctly.")