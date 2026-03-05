import requests
import json
import logging
from typing import Optional
from intent.intent_classifier import Intent
from config.constants import DEFAULT_OLLAMA_URL, DEFAULT_LLM_MODEL

class LLMIntentClassifier:
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_LLM_MODEL):
        self.ollama_url = ollama_url
        self.model = model
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """
You are the brain of a voice assistant on Windows. Your job is to classify user commands into structured JSON intents.
You have access to the following tools (intents):

1. **TRIGGER_N8N**: Use this for complex workflows, messaging, reminders, or anything that sounds like a multi-step automation.
   - `workflow`: A short slug describing the workflow (e.g., "send_slack", "create_reminder").
   - `parameters`: A dictionary of extracted slots (e.g., {"recipient": "John", "message": "Hello"}).

2. **CHAT**: Use this when the user is just chatting or asking a general question that doesn't require an action.
   - `response`: Your textual response to the user.

3. **SYSTEM_HEALTH_CHECK**: Use this when the user asks about the status, health, or performance of the assistant or its modules.
   - No slots required.

4. **INTRODUCE_SELF**: Use this when the user asks "Who are you?", "What is your name?", or "Tell me about yourself".
   - No slots required.
Output strictly JSON. Do not output markdown or explanations.
Example 1: "Send a message to John saying I'll be late"
{
  "intent": "TRIGGER_N8N",
  "slots": {
    "workflow": "send_message",
    "parameters": {
      "recipient": "John", 
      "message": "I'll be late"
    }
  }
}

Example 2: "Tell me a joke"
{
  "intent": "CHAT",
  "slots": {
    "response": "Why did the chicken cross the road? To get to the other side!"
  }
}

Example 3: "How is the system doing?"
{
  "intent": "SYSTEM_HEALTH_CHECK",
  "slots": {}
}
"""

    def classify(self, text: str) -> Optional[Intent]:
        payload = {
            "model": self.model,
            "prompt": f"User Command: {text}\nJSON Response:",
            "system": self.system_prompt,
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(self.ollama_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract JSON from the 'response' field
            llm_response = data.get("response", "{}")
            structured = json.loads(llm_response)
            
            intent_name = structured.get("intent")
            slots = structured.get("slots", {})
            
            if intent_name:
                return Intent(intent_name, slots)
            return None
            
        except Exception as e:
            logging.error(f"LLM Classification failed: {e}")
            return None
