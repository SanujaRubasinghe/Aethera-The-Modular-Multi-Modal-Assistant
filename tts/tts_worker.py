import threading
import queue
import time
import torch
import sounddevice as sd
from kokoro import KPipeline
import numpy as np

import config.constants as consts
from server.websocket_server import ws_server


class TTSWorker(threading.Thread):
    """
    Text-to-speech worker with barge-in support via wake-word.

    After finishing a turn it sets `turn_done_event` so the conversation
    manager can auto-trigger follow-up listening.  During playback, it 
    monitors `wake_event`. if the user says "computer", the detector sets 
    the event, which stops playback immediately.
    """

    def __init__(self, wake_event, shutdown_event, response_queue,
                 conversation_event=None):
        super().__init__(daemon=True)
        self.wake_event = wake_event
        self.shutdown_event = shutdown_event
        self.response_queue = response_queue
        self.conversation_event = conversation_event  # stays set while in conversation

        self.pipeline = None
        self.sample_rate = 24000
        self._lock = threading.Lock()
        self._stop_requested = False

        # Turn coordination
        self.turn_done_event = threading.Event()   # signalled when turn finishes
        self.last_response_was_question = False     # for agent-initiated listening

    # ── Public API ───────────────────────────────────────────────────

    def stop_current(self):
        with self._lock:
            self._stop_requested = True
            self.wake_event.set()

    # ── Playback ─────────────────────────────────────────────────────

    def _play_interruptible(self, audio_tensor):
        audio = audio_tensor.detach().cpu().numpy().astype(np.float32)

        with sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32'
        ) as stream:
            chunk_size = self.sample_rate // 10  # 100ms chunks

            for i in range(0, len(audio), chunk_size):
                if (self.shutdown_event.is_set() or
                        self._stop_requested or
                        self.wake_event.is_set()):
                    break

                chunk = audio[i:i + chunk_size]
                stream.write(chunk.reshape(-1, 1))

    # ── Main loop ────────────────────────────────────────────────────

    def run(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = KPipeline(lang_code="a", device=device)

        print("TTSWorker [IDLE]")
        self.turn_done_event.set()  # Start in idle state

        while not self.shutdown_event.is_set():
            try:
                item = self.response_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                print("TTSWorker: End-of-Turn marker received")
                self.turn_done_event.set()
                self.response_queue.task_done()
                continue
            
            # If we were previously idle, this is the start of a turn
            if self.turn_done_event.is_set():
                self.turn_done_event.clear()
                self.last_response_was_question = False

            text = item
            if not text:
                continue

            with self._lock:
                self._stop_requested = False
                self.wake_event.clear()
                ws_server.broadcast('state', 'speaking')

            # Detect if this response is a question (agent-initiated listening)
            is_question = text.rstrip().endswith("?")

            interrupted = False
            try:
                segments = self.pipeline(text, voice="af_bella")
                for gs, ps, audio_tensor in segments:
                    if self.shutdown_event.is_set():
                        break

                    # Check wake word interruption before each segment
                    if self.wake_event.is_set():
                        print("TTSWorker: Wake-word interruption detected — stopping playback")
                        interrupted = True
                        break

                    self._play_interruptible(audio_tensor)

                    if self.wake_event.is_set():
                        print("TTSWorker: Wake-word interruption detected — stopping playback")
                        interrupted = True
                        break

            except Exception as e:
                print(f"TTSWorker ERROR: {e}")
            finally:
                ws_server.broadcast('state', 'idle')

            self.response_queue.task_done()

            # Signal turn completion
            self.last_response_was_question = is_question

            if interrupted:
                # Wake-word barge-in: the wake detector already set the event
                # whisper_stt will pick it up and start listening.
                print("TTSWorker: Interrupted → handing over to STT")
                if self.conversation_event:
                    self.conversation_event.set()
            # Note: self.turn_done_event is now ONLY set when the 'None' marker is received.

        print("TTSWorker [SHUTDOWN]")
