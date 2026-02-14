# STT constants
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30 # VAD frame duration
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
SILENCE_TIMEOUT = 2        
VAD_MODE = 2    

# TTS constants

# n8n webhook url
N8N_WEBHOOK_URL="http://localhost:5678/webhook/voice-assistant"

# LLM Constants
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_LLM_MODEL = "gemma3:4b"

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