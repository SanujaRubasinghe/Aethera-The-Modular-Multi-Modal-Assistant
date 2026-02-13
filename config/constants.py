# STT constants
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30 # VAD frame duration
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
SILENCE_TIMEOUT = 2        
VAD_MODE = 2    

# TTS constants
FIRST_BOOT_RESPONSES = [
    "Hello. I am set up and ready to help. What would you like to do?",
    "Hi. Your voice assistant is now ready. How can I assist you?",
    "Setup is complete. I am ready for your first request.",
    "I am online and ready. What would you like me to handle?",
    "Everything is ready to go. How can I help you today?",
    "Welcome. I am fully initialized and listening.",
    "Your assistant is now active. What can I do for you?",
    "Initialization complete. Please tell me your first task.",
    "I am ready to assist. What would you like me to do?",
    "System is ready. How can I help you get started?"
]

# n8n webhook url
N8N_WEBHOOK_URL="http://localhost:5678/webhook/voice-assistant"

# LLM Constants
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_LLM_MODEL = "gemma3:4b"

# Vision constants
CAMERA_FPS=30