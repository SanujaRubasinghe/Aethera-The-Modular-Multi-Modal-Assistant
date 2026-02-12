import pvporcupine
import struct
import pyaudio
import time

class WakeWordDetector:
    def __init__(self, wake_event, shutdown_event, response_queue):
        self.wake_event = wake_event
        self.shutdown_event = shutdown_event
        self.response_queue = response_queue

        self.porcupine = pvporcupine.create(keywords=["computer"])
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

    def listen(self):
        print("WakeWordDetector [IDLE]")
        while not self.shutdown_event.is_set():
            pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)

            keyword_index = self.porcupine.process(pcm)
            if keyword_index >= 0:
                print("Yes Sir?")
                self.wake_event.set()
                
                # Clear existing responses (handle interrupts)
                with self.response_queue.mutex:
                    self.response_queue.queue.clear()
                
                self.response_queue.put("Yes sir?")
        self.stop()
        print("WakeWordDetector [SHUTDOWN]")

    def stop(self):
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.pa.terminate()
        self.porcupine.delete()
                