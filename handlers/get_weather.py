from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from config.constants import N8N_WEBHOOK_URL
from state.assistant_state import AssistantState

import requests

class GetWeatherHandler(BaseHandler):
    INTENT_NAME = "GET_WEATHER"

    def handle(self, intent, state: AssistantState, permission_manager):
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
        return TaskResult(True, message.get("content", "Sorry there was an error retrieving the weather information."))