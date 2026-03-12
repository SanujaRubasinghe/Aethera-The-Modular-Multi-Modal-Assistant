import torch
import warnings
warnings.filterwarnings('ignore')
torch.backends.cudnn.benchmark = True

import threading
import time
import queue
import config.constants as consts

from wakeword.wake_word_detection import WakeWordDetector
from stt.whisper_stt import WhisperSTT
from tts.tts_worker import TTSWorker
from vision.camera_manager import CameraManager
from state.assistant_state import AssistantState
from state.bootstrap import bootstrap_existing_apps
from server.websocket_server import ws_server
from assistant.terminal_input import TerminalInput

from core.agent.AetheraAgent import AetheraAgent
from core.memory.AetheraMemory import AetheraMemory
from core.proactive_engine.ProactiveEngine import ProactiveEngine
from tools.system_tools import ALL_TOOLS, set_assistant_state
from tools.memory_tools import MEMORY_TOOLS, set_memory


class AgentWorker(threading.Thread):
    """
    Pulls raw text from text_queue, sends it to AetheraAgent,
    and streams sentences into response_queue for TTS.
    """

    def __init__(self, agent: AetheraAgent, text_queue: queue.Queue,
                 response_queue: queue.Queue, shutdown_event: threading.Event,
                 security_gate=None):
        super().__init__(daemon=True)
        self.agent = agent
        self.text_queue = text_queue
        self.response_queue = response_queue
        self.shutdown_event = shutdown_event
        self.security_gate = security_gate

    def run(self):
        print("AgentWorker [RUNNING]")
        while not self.shutdown_event.is_set():
            try:
                text = self.text_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not text:
                continue

            # Security check (face authentication)
            if self.security_gate and not self.security_gate.allow(text):
                self.response_queue.put("Access denied. Owner not recognized.")
                continue

            ws_server.broadcast('state', 'thinking')

            try:
                for sentence in self.agent.stream_response(text):
                    if self.shutdown_event.is_set():
                        break
                    self.response_queue.put(sentence)
                # Mark end of turn for TTS sync
                self.response_queue.put(None)
            except Exception as e:
                print(f"AgentWorker ERROR: {e}")
                self.response_queue.put("I seem to have encountered a difficulty.")

        print("AgentWorker [STOPPED]")




class ConversationManager(threading.Thread):
    """
    Coordinates the natural flow:
    1. Watches for TTS to finish a turn.
    2. After a brief guard delay, triggers the follow-up window (wake_event + conversation_event).
    3. Manages the conversation state.
    """
    def __init__(self, tts_worker: TTSWorker, wake_event: threading.Event, 
                 shutdown_event: threading.Event, conversation_event: threading.Event):
        super().__init__(daemon=True)
        self.tts = tts_worker
        self.wake_event = wake_event
        self.shutdown_event = shutdown_event
        self.conversation_event = conversation_event

    def run(self):
        print("ConversationManager [RUNNING]")
        while not self.shutdown_event.is_set():
            # Wait for TTS to finish a turn
            if not self.tts.turn_done_event.wait(timeout=0.5):
                continue
            
            self.tts.turn_done_event.clear()
            
            # Brief guard to avoid hearing own echo
            time.sleep(consts.BARGE_IN_ECHO_GUARD_S)
            
            if self.shutdown_event.is_set():
                break

            # If the response was a question, we want a follow-up window
            if self.tts.last_response_was_question:
                print(f"ConversationManager: Turn over. Question detected. Starting follow-up window...")
                self.conversation_event.set()
                self.wake_event.set()
            else:
                # No question detected, do not trigger STT follow-up
                self.conversation_event.clear()
        
        print("ConversationManager [STOPPED]")


class VoiceAssistant:
    def __init__(self):
        self.text_queue = queue.Queue()       # raw transcribed text
        self.response_queue = queue.Queue()   # sentences for TTS

        first_boot_response = "Starting up. Diagnostics in progress."
        self.response_queue.put(first_boot_response)

        self.wake_event = threading.Event()
        self.shutdown_event = threading.Event()
        self.conversation_event = threading.Event() # Set during follow-up windows

        # ── State ────────────────────────────────────────────────────
        self.state = AssistantState()
        bootstrap_existing_apps(self.state)
        self.state.sync_focus_from_os()

        # ── Memory & Agent ───────────────────────────────────────────
        self.memory = AetheraMemory()

        # Inject shared state into tool modules
        set_assistant_state(self.state)
        set_memory(self.memory)

        all_tools = ALL_TOOLS + MEMORY_TOOLS
        self.agent = AetheraAgent(tools=all_tools, memory=self.memory)

        # ── Vision ───────────────────────────────────────────────────
        self.vision_manager = CameraManager(shutdown_event=self.shutdown_event)
        from vision.face_recognizer import FaceRecognizer
        from vision.security_gate import SecurityGate
        from vision.gesture_controller import GestureController

        self.security_gate = SecurityGate(
            state=self.state, camera=self.vision_manager,
            response_queue=self.response_queue,
        )
        self.face_recognizer = FaceRecognizer(
            camera=self.vision_manager, state=self.state,
            response_queue=self.response_queue,
            shutdown_event=self.shutdown_event,
            security_gate=self.security_gate,
        )
        self.gesture_controller = GestureController(
            camera=self.vision_manager, state=self.state,
            intent_queue=self.text_queue,  # gestures can inject text too
            shutdown_event=self.shutdown_event,
        )

        # ── Audio pipeline ───────────────────────────────────────────
        self.wake_detector = WakeWordDetector(
            wake_event=self.wake_event,
            shutdown_event=self.shutdown_event,
            response_queue=self.response_queue,
        )
        self.stt_worker = WhisperSTT(
            wake_event=self.wake_event,
            shutdown_event=self.shutdown_event,
            text_queue=self.text_queue,
            conversation_event=self.conversation_event
        )
        self.tts_worker = TTSWorker(
            wake_event=self.wake_event,
            response_queue=self.response_queue,
            shutdown_event=self.shutdown_event,
            conversation_event=self.conversation_event
        )

        # ── Flow Coordination ──
        self.conv_manager = ConversationManager(
            tts_worker=self.tts_worker,
            wake_event=self.wake_event,
            shutdown_event=self.shutdown_event,
            conversation_event=self.conversation_event
        )

        # ── Agent worker (replaces CentralController + Dispatcher) ──
        self.agent_worker = AgentWorker(
            agent=self.agent,
            text_queue=self.text_queue,
            response_queue=self.response_queue,
            shutdown_event=self.shutdown_event,
            security_gate=self.security_gate,
        )


        # ── Terminal input ───────────────────────────────────────────
        self.terminal_input = TerminalInput(
            text_queue=self.text_queue,
            shutdown_event=self.shutdown_event,
        )

        # ── Module health ────────────────────────────────────────────
        self.state.update_module_status("wake_word", True)
        self.state.update_module_status("stt", True)
        self.state.update_module_status("tts", True)
        self.state.update_module_status("agent", True)

        # ── Proactive Engine ─────────────────────────────────────────
        self.proactive_engine = ProactiveEngine(
            AETHERA=self.agent,
            response_queue=self.response_queue,
            shutdown_event=self.shutdown_event,
        )
        self.proactive_engine.register_defaults()

        self.threads = []

    def start(self):
        if not self.shutdown_event.is_set() and self.threads:
            print("Voice Assistant is already running.")
            return

        self.shutdown_event.clear()
        self.wake_event.clear()

        wake_thread = threading.Thread(target=self.wake_detector.listen, args=(self.conversation_event,))
        stt_thread = threading.Thread(target=self.stt_worker.listen)

        self.vision_manager.start()

        print("VoiceAssistant: Waiting for camera initialization...")
        self.vision_manager.ready_event.wait(timeout=8.0)
        self.state.update_module_status("vision", self.vision_manager.available)

        if not self.vision_manager.available:
            print("VoiceAssistant: Camera not found. Disabling vision modules.")
            self.response_queue.put(
                "Warning: Camera module could not be found. "
                "Vision features (FaceID, Gestures) are disabled."
            )
            self.vision_enabled = False
        else:
            print("VoiceAssistant: Camera found. Enabling vision modules.")
            self.vision_enabled = True
            self.face_recognizer.start()
            self.gesture_controller.start()
            self.state.update_module_status("face_recognition", True)
            self.state.update_module_status("gesture_control", True)

        ws_thread = threading.Thread(target=ws_server.start, daemon=True)
        ws_thread.start()

        wake_thread.start()
        stt_thread.start()
        self.terminal_input.start()
        self.tts_worker.start()
        self.agent_worker.start()
        self.conv_manager.start()
        self.proactive_engine.start()

        self.threads = [wake_thread, stt_thread, ws_thread, self.conv_manager, self.proactive_engine]
        print("\nVoice Assistant started. All systems online.")

    def stop(self):
        print("Shutting down...\n")
        self.shutdown_event.set()
        self.tts_worker.stop_current()
        print("\nExited cleanly")


if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.start()

    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        assistant.stop()