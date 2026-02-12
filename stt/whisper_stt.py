import time
import queue
import numpy as np
import webrtcvad
import sounddevice as sd
from faster_whisper import WhisperModel

from intent.intent_classifier import RuleBasedIntentClassifier

import config.constants as consts

class WhisperSTT:
    def __init__(self, wake_event, shutdown_event, intent_queue, response_queue):
        self.wake_event = wake_event
        self.shutdown_event = shutdown_event
        self.intent_queue = intent_queue
        self.response_queue = response_queue

        # VAD setup
        self.vad = webrtcvad.Vad(consts.VAD_MODE)
        self.audio_queue = queue.Queue()

        self.model = WhisperModel("medium.en", device="cuda")

        # intent classifier
        self.intent_classifier = RuleBasedIntentClassifier(self.response_queue)

    def _audio_callback(self, indata, frame, time_info, status):
        if status:
            return
        pcm16 = (indata[:, 0] * 32768).astype(np.int16).tobytes()
        self.audio_queue.put(pcm16)

    def listen(self):
        print("WhisperSTT [IDLE]")
        while not self.shutdown_event.is_set():
            triggered = self.wake_event.wait(timeout=0.2)
            if self.shutdown_event.is_set():
                break
            if not triggered:
                continue

            self.wake_event.clear()
            print("WhisperSTT [LISTENING]")

            self._run_stt_session()
        print("WhisperSTT [SHUTDOWN]")

    def _run_stt_session(self):
        speech_frames = []
        last_voice_time = time.time()

        with sd.InputStream(
            samplerate=consts.SAMPLE_RATE,
            channels=1,
            blocksize=consts.FRAME_SIZE,
            dtype="float32",
            callback=self._audio_callback
        ):
            while not self.shutdown_event.is_set():
                try:
                    frame = self.audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                # Checking for VAD
                is_speech = self.vad.is_speech(frame, consts.SAMPLE_RATE)

                if is_speech:
                    speech_frames.append(frame)
                    last_voice_time = time.time()
                else:
                    if time.time() - last_voice_time >= consts.SILENCE_TIMEOUT:
                        break
        
        if not speech_frames:
            print("No speech detected, returning to [IDLE]")
            return
        
        self._process_whisper(speech_frames)

    def _process_whisper(self, frames):
        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, np.int16).astype(np.float32) / 32768.0

        segments, _ = self.model.transcribe(audio_np, beam_size=5)

        text = ""
        for segment in segments:
            text += segment.text + " "
        if text:
            intents = self.intent_classifier.classify(text)
            
            # Check for fallback
            if len(intents) == 1 and intents[0].name == "fallback":
                print("Regex failed, trying LLM...")
                try:
                    from intent.llm_intent_classifier import LLMIntentClassifier
                    llm_classifier = LLMIntentClassifier() # TODO: Instantiate once in __init__ for performance
                    llm_intent = llm_classifier.classify(text)
                    if llm_intent:
                        print(f"LLM Classification: {llm_intent.name} {llm_intent.slots}")
                        intents = [llm_intent]
                except Exception as e:
                    print(f"LLM Fallback failed: {e}")

            for intent in intents:
                self.intent_queue.put(intent)

            # intents_json = self.intent_classifier.classify_json(text)
            # print(intents_json)
            
        else:
            print("Speech detected but no transcription")
