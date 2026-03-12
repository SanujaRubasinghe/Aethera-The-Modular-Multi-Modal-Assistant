# STT constants
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30 # VAD frame duration
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
SILENCE_TIMEOUT = 2        
VAD_MODE = 2    

# TTS constants

# Conversation flow constants
FOLLOW_UP_WINDOW_S = 6         # seconds to keep listening after TTS finishes
BARGE_IN_ECHO_GUARD_S = 0.3   # ignore mic briefly after TTS stops (echo suppression)
BARGE_IN_SETTLE_S = 0.5       # ignore mic briefly after TTS starts playback
BARGE_IN_CONSECUTIVE_FRAMES = 5 # number of 30ms frames of speech required to trigger


# n8n webhook url
N8N_WEBHOOK_URL="http://localhost:5678/webhook/voice-assistant"

# LLM Constants
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_LLM_MODEL = "qwen2.5:14b"

# Vision constants
CAMERA_FPS=30
FACE_DATA_PATH='./vision/face_encodings/face_embedding.pkl'
FACE_MATCH_THRESHOLD=0.6
FACE_RECOGNITION_INTERVAL=5.0
AUTH_TIMEOUT_SECONDS=15

GESTURE_DEBOUNCE_MS=500

INTRUSION_DATA_DIR='./data/intrusion'
INTRUSION_CAPTURE_COOLDOWN=30.0
INTRUSION_RETENTION_DAYS=7

LOCK_ON_UNAUTHORIZED = True