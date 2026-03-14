import threading
import queue
import time
import numpy as np
from elevenlabs.play import play

import config.constants as consts
from server.websocket_server import ws_server
from tts.elevenlabs_tts import ElevenLabsTTS


class TTSWorker(threading.Thread):
    """
    Text-to-speech worker with barge-in support via wake-word,
    now using ElevenLabs (non-streaming) for high quality.
    """

    def __init__(self, wake_event, shutdown_event, response_queue,
                 conversation_event=None):
        super().__init__(daemon=True)
        self.wake_event = wake_event
        self.shutdown_event = shutdown_event
        self.response_queue = response_queue
        self.conversation_event = conversation_event  # stays set while in conversation

        self.tts = None
        self._lock = threading.Lock()
        self._stop_requested = False

        # Turn coordination
        self.turn_done_event = threading.Event()   # signalled when turn finishes
        self.last_response_was_question = False     # for agent-initiated listening

    # ── Public API ───────────────────────────────────────────────────

    def stop_current(self):
        with self._lock:
            self._stop_requested = True
            # Note: elevenlabs.play is blocking, so interruption 
            # might only be checked between sentences if we split them.
            self.wake_event.set()

    # ── Main loop ────────────────────────────────────────────────────

    def run(self):
        try:
            self.tts = ElevenLabsTTS()
        except Exception as e:
            print(f"TTSWorker FAILED TO INITIALIZE ElevenLabsTTS: {e}")
            return

        print("TTSWorker [IDLE] (ElevenLabs)")
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

            try:
                print(f"TTSWorker: Generating and playing: {text}")
                audio = self.tts.generate(text)
                
                # Check for interruption and valid audio before playing
                if audio and not (self.shutdown_event.is_set() or self._stop_requested or self.wake_event.is_set()):
                    play(audio)

            except Exception as e:
                print(f"TTSWorker ERROR: {e}")
            finally:
                ws_server.broadcast('state', 'idle')

            self.response_queue.task_done()

            # Signal turn completion
            self.last_response_was_question = is_question

            if (self._stop_requested or self.wake_event.is_set()):
                # Wake-word barge-in: the wake detector already set the event
                # whisper_stt will pick it up and start listening.
                print("TTSWorker: Interrupted → handing over to STT")
                if self.conversation_event:
                    self.conversation_event.set()

        print("TTSWorker [SHUTDOWN]")
