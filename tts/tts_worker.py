import threading
import queue
import torch
import sounddevice as sd
from kokoro import KPipeline
import numpy as np

class TTSWorker(threading.Thread):
    def __init__(self, wake_event, shutdown_event, response_queue):
        super().__init__(daemon=True)
        self.wake_event = wake_event
        self.shutdown_event = shutdown_event
        self.response_queue = response_queue

        self.pipeline = None
        self.sample_rate = 24000
        self._lock = threading.Lock()
        self._stop_requested = False

    def stop_current(self):
        with self._lock:
            self._stop_requested = True
            self.wake_event.set()

    def _play_interruptible(self, audio_tensor):
        audio = audio_tensor.detach().cpu().numpy().astype(np.float32)
        
        with sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1, 
            dtype='float32'
        ) as stream:
            chunk_size = self.sample_rate // 10

            for i in range(0, len(audio), chunk_size):
                if self.shutdown_event.is_set() or self._stop_requested or self.wake_event.is_set():
                    break

                chunk = audio[i:i+chunk_size]
                stream.write(chunk.reshape(-1, 1))

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

            try:
                segments = self.pipeline(text, voice="af_bella")
                for gs, ps, audio_tensor in segments:
                    if self.shutdown_event.is_set():
                        break
                    self._play_interruptible(audio_tensor)
            except Exception as e:
                print(f"TTSWorker ERROR: {e}")

            self.response_queue.task_done()

        print("TTSWorker [SHUTDOWN]")
