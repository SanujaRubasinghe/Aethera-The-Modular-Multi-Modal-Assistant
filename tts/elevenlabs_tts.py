import os
import re
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsTTS:
    def __init__(self, api_key: str = None, voice_id: str = "JBFqnCBsd6RMkjVDRZzb", model_id: str = "eleven_v3"):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API Key not found. Please set ELEVENLABS_API_KEY in .env")
        
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_id = voice_id
        self.model_id = model_id
        self._tag_pattern = re.compile(r'\[.*?\]')

    def generate(self, text: str):
        """
        Generates audio using the convert method as seen in tests/test_elevenlabs.py.
        Ensures there is actual text content to avoid ElevenLabs 400 errors.
        """
        # ElevenLabs fails with 400 if text is empty after removing tags and emojis.
        # We check if there's any non-tag text content.
        clean_text = self._tag_pattern.sub('', text).strip()
        if not clean_text:
            print(f"ElevenLabsTTS: Skipping generation for text containing only tags: {text}")
            return None

        return self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            model_id=self.model_id,
            output_format="mp3_44100_128",
        )
