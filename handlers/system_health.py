import logging
import requests
import time
from typing import Dict, Any
from handlers.base_handler import BaseHandler
from state.assistant_state import AssistantState
from controllers.task_dispatcher import TaskResult
from config.constants import DEFAULT_OLLAMA_URL, N8N_WEBHOOK_URL, DEFAULT_LLM_MODEL

class SystemHealthHandler(BaseHandler):
    INTENT_NAME = "SYSTEM_HEALTH_CHECK"

    def handle(self, intent, state: AssistantState, permission_manager):
        health_report = {
            "modules": state.module_status,
            "services": {
                "llm": self._check_llm(),
                "n8n": self._check_n8n()
            }
        }

        # Generate a friendly summary using the LLM
        summary = self._generate_llm_summary(health_report)
        return TaskResult(True, summary, data=health_report)

    def _check_llm(self) -> bool:
        try:
            # Check if Ollama is running
            response = requests.get(DEFAULT_OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=2)
            return response.status_code == 200
        except:
            return False

    def _check_n8n(self) -> bool:
        try:
            base_url = N8N_WEBHOOK_URL.split("/webhook/")[0]
            response = requests.get(base_url, timeout=2)
            return response.status_code == 200
        except:
            return False

    def _generate_llm_summary(self, health_data: Dict[str, Any]) -> str:
        prompt = f"""
Report the health status of the voice assistant based on the following data:
{health_data}

You are a system health monitoring agent.

Your task is to provide a concise, professional, and natural spoken status report.

CRITICAL RULES:
- Output plain text only.
- No markdown.
- No bullet points.
- No emojis.
- No special characters.
- No technical jargon unless necessary.
- Keep it under three short sentences.
- Sound calm, confident, and intelligent.
- Make it suitable for text-to-speech playback.
- Do not add explanations beyond the status report.
- Do not speculate about unknown information.

GOAL:
Summarize overall system health in a way that feels like a composed and capable assistant reporting its state.

STYLE:
- Natural spoken language.
- Slightly conversational but professional.
- Avoid robotic phrasing.
- Avoid repeating input wording verbatim.
- Do not sound alarmist unless there is a critical issue.

FORMAT GUIDELINES:

If everything is functioning normally:
Provide a smooth confirmation such as:
"All systems are operating normally."
or
"Everything is running as expected."

If minor issues exist:
Briefly mention affected modules and indicate they are being monitored.

If significant issues exist:
Clearly name the affected modules and indicate attention is required.

Never output anything outside the status report.
"""
        payload = {
            "model": DEFAULT_LLM_MODEL,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(DEFAULT_OLLAMA_URL, json=payload)
            response.raise_for_status()
            return response.json().get("response", "System check complete. All modules appear stable.")
        except Exception as e:
            logging.error(f"Health summary generation failed: {e}")
            return "System check complete. I'm having trouble connecting to my central brain for a detailed report, but most local modules are running."
