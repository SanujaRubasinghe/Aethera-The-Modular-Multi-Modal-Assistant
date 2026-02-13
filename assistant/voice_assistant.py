import torch
import warnings
warnings.filterwarnings('ignore')
torch.backends.cudnn.benchmark = True

from wakeword.wake_word_detection import WakeWordDetector
from stt.whisper_stt import WhisperSTT
from tts.tts_worker import TTSWorker
from controllers.central_controller import CentralController
from controllers.task_dispatcher import TaskDispatcher
from controllers.handler_loader import load_handlers
from controllers.permission_manager import PermissionManager
from vision.camera_manager import CameraManager
from state.assistant_state import AssistantState
from state.bootstrap import bootstrap_existing_apps
import handlers

import threading
import time
import queue

from config.constants import FIRST_BOOT_RESPONSES
import random

class VoiceAssistant:
    def __init__(self):
        self.intent_queue = queue.Queue()
        self.response_queue = queue.Queue()

        first_boot_response = random.choice(FIRST_BOOT_RESPONSES)
        self.response_queue.put(first_boot_response)
        
        self.wake_event = threading.Event()
        self.shutdown_event = threading.Event()
        
        self.state = AssistantState()
        bootstrap_existing_apps(self.state)
        self.state.sync_focus_from_os()
        
        self.permission_manager = PermissionManager(self.intent_queue, self.response_queue, self.wake_event)
        self.dispatcher = TaskDispatcher(self.state, permission_manager=self.permission_manager)
        
        load_handlers(self.dispatcher, handlers)

        self.vision_manager = CameraManager(shutdown_event=self.shutdown_event)
        
        self.wake_detector = WakeWordDetector(wake_event=self.wake_event, shutdown_event=self.shutdown_event, response_queue=self.response_queue)
        self.stt_worker = WhisperSTT(wake_event=self.wake_event, shutdown_event=self.shutdown_event, intent_queue=self.intent_queue, response_queue=self.response_queue)
        
        self.tts_worker = TTSWorker(wake_event=self.wake_event, response_queue=self.response_queue, shutdown_event=self.shutdown_event)
        self.controller = CentralController(intent_queue=self.intent_queue, resposne_queue=self.response_queue, dispatcher=self.dispatcher, shutdown_event=self.shutdown_event)
        
        self.threads = []

    def start(self):
        if not self.shutdown_event.is_set() and self.threads:
             print("Voice Assistant is already running.")
             return

        self.shutdown_event.clear()
        self.wake_event.clear()
        
        wake_thread = threading.Thread(target=self.wake_detector.listen)
        stt_thread = threading.Thread(target=self.stt_worker.listen)
        
        self.vision_manager.start()
        
        # Wait for camera to initialize and check availability
        self.vision_manager.ready_event.wait(timeout=2.0)
        if not self.vision_manager.available:
            self.response_queue.put("Error encountered. Camera module could not be found. All vision-related features are disabled.")
            self.vision_enabled = False
        else:
            self.vision_enabled = True

        wake_thread.start()
        stt_thread.start()
        self.tts_worker.start()
        self.controller.start()
        
        self.threads = [wake_thread, stt_thread]
        print("\nVoice Assistant started.")

    def stop(self):
        print("Shutting down...\n")
        self.shutdown_event.set()
        self.tts_worker.stop_current()
        
        # We don't join threads here to avoid blocking GUI if threads are stuck, 
        # but in a production app we should handle this more gracefully.
        # self.tts_worker.join(timeout=0.2)
        # self.controller.join(timeout=0.2)
        print("\nExited cleanly")

if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.start()
    
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        assistant.stop()