from handlers.base_handler import BaseHandler
from os_control.screenshot import capture_monitor_for_screen_read
from state.assistant_state import AssistantState
from controllers.task_dispatcher import TaskResult

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText
from accelerate import Accelerator

import requests
from config.constants import N8N_WEBHOOK_URL

class ReadScreenHandler(BaseHandler):
    INTENT_NAME = "READ_SCREEN"

    def __init__(self):
        self.device = Accelerator().device
        self.processor = AutoProcessor.from_pretrained("HuggingFaceTB/SmolVLM-256M-Instruct")
        self.model = AutoModelForImageTextToText.from_pretrained(
            "HuggingFaceTB/SmolVLM-256M-Instruct",
            dtype=torch.bfloat16,
        ).to(self.device)

    def handle(self, intent, state: AssistantState, permission_manager):
        try:
            img = capture_monitor_for_screen_read()

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": "What is on this image?"},
                        {"type": "text", "text": "Do NOT mention that this is a screen shot."},
                    ]
                },
            ]

            prompt = self.processor.apply_chat_template(messages, add_generation_prompt=True)
            inputs = self.processor(text=prompt, images=[img], return_tensors="pt")
            inputs = inputs.to(self.device)

            # Generate outputs
            generated_ids = self.model.generate(**inputs, max_new_tokens=500)
            generated_texts = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )
            extracted_output = self.extract_assistant(generated_texts[0])
            print(generated_texts[0])

            payload = {"intent_name": self.INTENT_NAME, "data": extracted_output}
            headers = {"Content-Type": "application/json"}
            response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers)
            all_data = response.json()
            message = all_data.get("message")

            return TaskResult(True, message.get("content", "No content returned from webhook"))
        except Exception:
            return TaskResult(False, "Sorry, I am unable to look at the screen at the moment.")
    
    @staticmethod
    def extract_assistant(text):
        if "Assistant:" in text:
            return text.split("Assistant:", 1)[1].strip()
        return text.strip()

