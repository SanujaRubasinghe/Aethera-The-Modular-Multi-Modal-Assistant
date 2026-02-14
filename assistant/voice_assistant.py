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


class VoiceAssistant:
    def __init__(self):
        self.intent_queue = queue.Queue()
        self.response_queue = queue.Queue()

        first_boot_response = "Starting up. Diagnostics in progress."
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
        from vision.face_recognizer import FaceRecognizer
        # from vision.gesture_controller import GestureController
        from vision.security_gate import SecurityGate

        self.face_recognizer = FaceRecognizer(
            camera=self.vision_manager,
            state=self.state,
            response_queue=self.response_queue,
            shutdown_event=self.shutdown_event
        )
        # self.gesture_controller = GestureController(
        #     camera=self.vision_manager,
        #     state=self.state,
        #     intent_queue=self.intent_queue,
        #     shutdown_event=self.shutdown_event
        # )
        self.security_gate = SecurityGate(state=self.state, camera=self.vision_manager)
        
        # Inject security gate into controller
        # TODO: CentralController needs update to check security_gate.allow(intent)
        
        self.wake_detector = WakeWordDetector(wake_event=self.wake_event, shutdown_event=self.shutdown_event, response_queue=self.response_queue)
        self.stt_worker = WhisperSTT(wake_event=self.wake_event, shutdown_event=self.shutdown_event, intent_queue=self.intent_queue, response_queue=self.response_queue)
        
        self.tts_worker = TTSWorker(wake_event=self.wake_event, response_queue=self.response_queue, shutdown_event=self.shutdown_event)
        self.controller = CentralController(
            intent_queue=self.intent_queue, 
            resposne_queue=self.response_queue, 
            dispatcher=self.dispatcher, 
            shutdown_event=self.shutdown_event,
            security_gate=self.security_gate
        )
        
        # Initial health update
        self.state.update_module_status("wake_word", True)
        self.state.update_module_status("stt", True)
        self.state.update_module_status("tts", True)
        self.state.update_module_status("central_controller", True)

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
        # Increased timeout to 8 seconds for slower systems or multiple backend attempts
        print("VoiceAssistant: Waiting for camera initialization...")
        self.vision_manager.ready_event.wait(timeout=8.0)
        self.state.update_module_status("vision", self.vision_manager.available)
        
        if not self.vision_manager.available:
            print("VoiceAssistant: Camera not found. Disabling vision modules.")
            self.response_queue.put("Warning: Camera module could not be found. Vision features (FaceID, Gestures) are disabled.")
            self.vision_enabled = False
            # Disable security gate in controller to prevent lockout
            self.controller.security_gate = None
        else:
            print("VoiceAssistant: Camera found. Enabling vision modules.")
            self.vision_enabled = True
            self.face_recognizer.start()
            # self.gesture_controller.start()
            self.state.update_module_status("face_recognition", True)
            self.state.update_module_status("gesture_control", False) # For now FALSE, later make it TRUE after fixing errors

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