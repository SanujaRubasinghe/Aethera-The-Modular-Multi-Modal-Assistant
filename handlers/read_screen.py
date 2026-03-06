from handlers.base_handler import BaseHandler
from os_control.screenshot import capture_monitor_for_screen_read
from state.assistant_state import AssistantState
from controllers.task_dispatcher import TaskResult

import torch
import numpy as np
import onnxruntime
from transformers import AutoConfig, AutoProcessor
import requests
from config.constants import N8N_WEBHOOK_URL

class ReadScreenHandler(BaseHandler):
    INTENT_NAME = "READ_SCREEN"

    def __init__(self):
        self.model_id = "HuggingFaceTB/SmolVLM-256M-Instruct"
        # Load config and processor
        self.config = AutoConfig.from_pretrained(self.model_id)
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        
        # Load ONNX sessions
        self.vision_session = onnxruntime.InferenceSession("vision/vlm_model/vision_encoder_q4.onnx")
        self.embed_session = onnxruntime.InferenceSession("vision/vlm_model/embed_tokens_q4.onnx")
        self.decoder_session = onnxruntime.InferenceSession("vision/vlm_model/decoder_model_merged_q4.onnx")
        
        # Set config values
        self.num_key_value_heads = self.config.text_config.num_key_value_heads
        self.head_dim = self.config.text_config.head_dim
        self.num_hidden_layers = self.config.text_config.num_hidden_layers
        self.eos_token_id = self.config.text_config.eos_token_id
        self.image_token_id = self.config.image_token_id

    def handle(self, intent, state: AssistantState, permission_manager):
        try:
            img = capture_monitor_for_screen_read()
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": "What is on this image?"},
                    ]
                },
            ]

            prompt = self.processor.apply_chat_template(messages, add_generation_prompt=True)
            inputs = self.processor(text=prompt, images=[img], return_tensors="np")

            # Prepare decoder inputs
            batch_size = inputs['input_ids'].shape[0]
            past_key_values = {
                f'past_key_values.{layer}.{kv}': np.zeros([batch_size, self.num_key_value_heads, 0, self.head_dim], dtype=np.float32)
                for layer in range(self.num_hidden_layers)
                for kv in ('key', 'value')
            }
            image_features = None
            input_ids = inputs['input_ids']
            attention_mask = inputs['attention_mask']
            position_ids = np.cumsum(inputs['attention_mask'], axis=-1)

            # Generation loop
            max_new_tokens = 500
            generated_tokens = np.array([[]], dtype=np.int64)
            
            for i in range(max_new_tokens):
                inputs_embeds = self.embed_session.run(None, {'input_ids': input_ids})[0]

                if image_features is None:
                    image_features = self.vision_session.run(
                        ['image_features'], 
                        {
                            'pixel_values': inputs['pixel_values'],
                            'pixel_attention_mask': inputs['pixel_attention_mask'].astype(np.bool_)
                        }
                    )[0]
                    # Merge text and vision embeddings
                    inputs_embeds[inputs['input_ids'] == self.image_token_id] = image_features.reshape(-1, image_features.shape[-1])

                logits, *present_key_values = self.decoder_session.run(None, dict(
                    inputs_embeds=inputs_embeds,
                    attention_mask=attention_mask,
                    position_ids=position_ids,
                    **past_key_values,
                ))

                # Update values for next generation loop
                input_ids = logits[:, -1].argmax(-1, keepdims=True)
                attention_mask = np.ones_like(input_ids)
                position_ids = position_ids[:, -1:] + 1
                for j, key in enumerate(past_key_values):
                    past_key_values[key] = present_key_values[j]

                generated_tokens = np.concatenate([generated_tokens, input_ids], axis=-1)
                if (input_ids == self.eos_token_id).all():
                    break

            output_text = self.processor.batch_decode(generated_tokens)[0]
            extracted_output = self.extract_assistant(output_text)

            payload = {"intent_name": self.INTENT_NAME, "data": extracted_output}
            headers = {"Content-Type": "application/json"}
            response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers)
            all_data = response.json()
            message = all_data.get("message")

            return TaskResult(True, message.get("content", "No content returned from webhook"))
        except Exception as e:
            print(f"ReadScreenHandler Error: {e}")
            return TaskResult(False, "Sorry, I am unable to look at the screen at the moment.")

    @staticmethod
    def extract_assistant(text):
        if "Assistant:" in text:
            return text.split("Assistant:", 1)[1].strip()
        return text.strip()

