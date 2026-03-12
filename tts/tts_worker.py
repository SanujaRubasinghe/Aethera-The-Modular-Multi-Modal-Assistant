import threading
import queue
import time
import torch
import sounddevice as sd
from kokoro import KPipeline
import numpy as np
import webrtcvad

import config.constants as consts
from server.websocket_server import ws_server


class TTSWorker(threading.Thread):
    """
    Text-to-speech worker with barge-in support.

    After finishing a turn it sets `turn_done_event` so the conversation
    manager can auto-trigger follow-up listening.  During playback a
    lightweight VAD monitor detects user speech and interrupts the output
    (barge-in).
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

        # Barge-in VAD state
        self._barge_vad = webrtcvad.Vad(consts.VAD_MODE)
        self._barge_stream = None
        self._barge_detected = threading.Event()
        self._playback_start_time = 0.0
        self._consecutive_speech_frames = 0

    # ── Public API ───────────────────────────────────────────────────

    def stop_current(self):
        with self._lock:
            self._stop_requested = True
            self.wake_event.set()

    # ── Barge-in mic monitor ─────────────────────────────────────────

    def _barge_audio_cb(self, indata, frames, time_info, status):
        """Robust callback: ignores initial echo and requires sustained speech."""
        if status or self._barge_detected.is_set():
            return

        # Settling time: ignore mic for the first few ms of playback to avoid initial echo
        if time.time() - self._playback_start_time < consts.BARGE_IN_SETTLE_S:
            return

        pcm16 = (indata[:, 0] * 32768).astype(np.int16).tobytes()
        try:
            if self._barge_vad.is_speech(pcm16, consts.SAMPLE_RATE):
                self._consecutive_speech_frames += 1
                if self._consecutive_speech_frames >= consts.BARGE_IN_CONSECUTIVE_FRAMES:
                    self._barge_detected.set()
            else:
                self._consecutive_speech_frames = 0
        except Exception:
            pass

    def _start_barge_monitor(self):
        """Open a mic stream that checks for speech during playback."""
        self._barge_detected.clear()
        self._consecutive_speech_frames = 0
        self._playback_start_time = time.time()
        try:
            self._barge_stream = sd.InputStream(
                samplerate=consts.SAMPLE_RATE,
                channels=1,
                blocksize=consts.FRAME_SIZE,
                dtype="float32",
                callback=self._barge_audio_cb,
            )
            self._barge_stream.start()
        except Exception as e:
            print(f"TTSWorker: Barge-in monitor failed to start: {e}")
            self._barge_stream = None

    def _stop_barge_monitor(self):
        if self._barge_stream is not None:
            try:
                self._barge_stream.stop()
                self._barge_stream.close()
            except Exception:
                pass
            self._barge_stream = None

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
                        self.wake_event.is_set() or
                        self._barge_detected.is_set()):
                    break

                chunk = audio[i:i + chunk_size]
                stream.write(chunk.reshape(-1, 1))

    # ── Main loop ────────────────────────────────────────────────────

    def run(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = KPipeline(lang_code="a", device=device)

        print("TTSWorker [IDLE]")

        while not self.shutdown_event.is_set():
            try:
                text = self.response_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not text:
                continue

            with self._lock:
                self._stop_requested = False
                self.wake_event.clear()
                self.turn_done_event.clear()
                ws_server.broadcast('state', 'speaking')

            # Detect if this response is a question (agent-initiated listening)
            is_question = text.rstrip().endswith("?")

            # Start barge-in monitor (mic listens for user speech during playback)
            self._start_barge_monitor()

            interrupted = False
            try:
                segments = self.pipeline(text, voice="af_bella")
                for gs, ps, audio_tensor in segments:
                    if self.shutdown_event.is_set():
                        break

                    # Check barge-in before each segment
                    if self._barge_detected.is_set():
                        print("TTSWorker: Barge-in detected — stopping playback")
                        interrupted = True
                        break

                    self._play_interruptible(audio_tensor)

                    if self._barge_detected.is_set():
                        print("TTSWorker: Barge-in detected — stopping playback")
                        interrupted = True
                        break

            except Exception as e:
                print(f"TTSWorker ERROR: {e}")
            finally:
                self._stop_barge_monitor()
                ws_server.broadcast('state', 'idle')

            self.response_queue.task_done()

            # Signal turn completion
            self.last_response_was_question = is_question

            if interrupted:
                # Barge-in: immediately trigger STT to capture what the user is saying
                print("TTSWorker: Barge-in → triggering STT")
                self.wake_event.set()
                if self.conversation_event:
                    self.conversation_event.set()
            else:
                # Normal turn end: signal for follow-up
                self.turn_done_event.set()

        print("TTSWorker [SHUTDOWN]")
