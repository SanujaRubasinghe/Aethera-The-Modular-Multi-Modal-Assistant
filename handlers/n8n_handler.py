from handlers.base_handler import BaseHandler
from controllers.task_dispatcher import TaskResult
from config.constants import N8N_WEBHOOK_URL
import requests
import logging

class N8NHandler(BaseHandler):
    INTENT_NAME = "TRIGGER_N8N"

    def handle(self, intent, state, permission_manager):
        workflow = intent.slots.get("workflow")
        parameters = intent.slots.get("parameters", {})
        
        if not workflow:
             # If LLM didn't provide a workflow slug, try to use the raw text or some default
             workflow = "default_voice_assistant"

        logging.info(f"Triggering n8n workflow: {workflow} with params: {parameters}")
        
        payload = {
            "workflow": workflow,
            "parameters": parameters,
            "raw_intent": intent.name,
            "user_context": {
                # Add any context if needed
            }
        }

        try:
            # We append the workflow slug to the base URL if needed, 
            # or just send it as part of the payload to a single entry point webhook.
            # Strategy: Single Entry Point Webhook that routes based on 'workflow' field.
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            message = data.get("message", "Workflow executed successfully.")
            
            # n8n can return a 'speech' field to be spoken
            speech = data.get("speech", message)
            
            return TaskResult(True, message=speech, data=data)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"n8n request failed: {e}")
            return TaskResult(False, f"Failed to connect to automation server")
        except Exception as e:
            logging.error(f"n8n handler error: {e}")
            return TaskResult(False, "An error occurred while executing the automation.")
