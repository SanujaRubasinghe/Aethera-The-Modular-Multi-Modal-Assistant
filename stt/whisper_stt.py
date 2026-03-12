import time
import queue
import numpy as np
import webrtcvad
import sounddevice as sd
from faster_whisper import WhisperModel

import config.constants as consts
from server.websocket_server import ws_server


class WhisperSTT:
    """
    Speech-to-text worker.

    Waits for the wake event, records speech until silence,
    transcribes with Whisper, and puts raw text onto the text_queue
    for the agent to process.
    """

    def __init__(self, wake_event, shutdown_event, text_queue):
        self.wake_event = wake_event
        self.shutdown_event = shutdown_event
        self.text_queue = text_queue

        # VAD setup
        self.vad = webrtcvad.Vad(consts.VAD_MODE)
        self.audio_queue = queue.Queue()

        self.model = WhisperModel("medium.en", device="cuda")

    def _audio_callback(self, indata, frame, time_info, status):
        if status:
            return
        pcm16 = (indata[:, 0] * 32768).astype(np.int16).tobytes()
        self.audio_queue.put(pcm16)

        # Calculate level for UI
        rms = np.sqrt(np.mean(indata**2))
        level = min(1.0, rms * 10)
        ws_server.broadcast('audio_level', level)

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
            ws_server.broadcast('state', 'listening')

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
            callback=self._audio_callback,
        ):
            while not self.shutdown_event.is_set():
                try:
                    frame = self.audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                is_speech = self.vad.is_speech(frame, consts.SAMPLE_RATE)

                if is_speech:
                    speech_frames.append(frame)
                    last_voice_time = time.time()
                else:
                    if time.time() - last_voice_time >= consts.SILENCE_TIMEOUT:
                        ws_server.broadcast('state', 'processing')
                        break

        if not speech_frames:
            print("No speech detected, returning to [IDLE]")
            ws_server.broadcast('state', 'idle')
            return

        self._process_whisper(speech_frames)
        ws_server.broadcast('state', 'idle')

    def _process_whisper(self, frames):
        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, np.int16).astype(np.float32) / 32768.0

        segments, _ = self.model.transcribe(audio_np, beam_size=5)

        text = ""
        for segment in segments:
            text += segment.text + " "

        text = text.strip()
        if text:
            print(f"WhisperSTT [TRANSCRIBED]: {text}")
            ws_server.broadcast('transcript', text)
            self.text_queue.put(text)
        else:
            print("Speech detected but no transcription")
