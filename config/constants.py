# STT constants
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30 # VAD frame duration
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
SILENCE_TIMEOUT = 2        
VAD_MODE = 2       

# n8n webhook url
N8N_WEBHOOK_URL="http://localhost:5678/webhook/voice-assistant"

# LLM Constants
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_LLM_MODEL = "llama3"