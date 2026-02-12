import threading
import time

class WakeHandler(threading.Thread):
    def __init__(self, wake_event, tts_worker, shutdown_event):
        super().__init__(daemon=True)
        self.wake_event = wake_event
        self.tts = tts_worker
        self.shutdown_event = shutdown_event

    def run(self):
        while not self.shutdown_event.is_set():
            if self.wake_event.wait(timeout=0.1):
                if self.shutdown_event.is_set():
                    break

                self.tts.stop_current()

                self.tts.say("Yes sir?")
                self.wake_event.clear()
