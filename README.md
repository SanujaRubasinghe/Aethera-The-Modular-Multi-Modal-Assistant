# Aethera: The Modular Multi-Modal Assistant

> [!CAUTION]
> **Project Under Development**: Aethera is currently in active development. Core vision and visual components are being implemented. Early preview stage.

**Aethera** is a premium multi-modal assistant merging local LLM intelligence with computer vision. Experience advanced voice control, biometric face security with intrusion logging, and a 22-gesture library for touchless OS navigation. Reactive 3D visuals and n8n automation make it a powerful, privacy-first hub for modern Windows workflows.

---

## ✨ Key Features

### 🎙️ Advanced Voice System
- **Intelligent Intent Recognition**: Powered by local LLMs (Ollama/llama3) for natural language understanding.
- **Whisper STT**: High-accuracy, low-latency speech-to-text using Faster-Whisper.
- **Neural TTS**: Expressive text-to-speech with multiple backend support (Kokoro/pyttsx3).
- **Proactive Context**: Real-time awareness of active applications and OS state.

### 👁️ Integrated Vision System
- **Face Recognition Security**: Biometric "Security Gate" that greets you and blocks unauthorized access.
- **Intrusion Detection**: Captures photos of unauthorized users and reports them upon your return.
- **Gesture Control**: 22+ custom gestures for touchless control of Windows, media, and navigation.
- **MediaPipe Powered**: Real-time hand landmark tracking with robust heuristic classification.

### ⚙️ Automation & Control
- **n8n Integration**: Trigger complex multi-step workflows directly via voice or gesture.
- **OS Automation**: Direct control over Windows volume, brightness, and applications.
- **Plugin System**: Easily add new capabilities by dropping in new `BaseHandler` modules.

### 🎨 Visual Experience
- **Particle Sphere Aura**: A speech-reactive 3D particle sphere that visualizes the assistant's state.
- **Modular Dashboard**: A crisp, functional Tkinter control panel for managing apps, macros, and vision settings.

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Input Layer
        Mic[Microphone] --> STT[Whisper STT]
        Cam[Camera] --> CM[Camera Manager]
    end

    subgraph Vision Layer
        CM --> FR[Face Recognizer]
        CM --> GC[Gesture Controller]
        CM --> IL[Intrusion Logger]
    end

    subgraph Core
        STT -->|Intent| CC[Central Controller]
        GC -->|Intent| CC
        FR -->|Auth State| CC
        CC --> TD[Task Dispatcher]
    end

    subgraph Output Layer
        TD --> Handlers[Modular Handlers]
        Handlers -->|Webhook| n8n[n8n Automation]
        Handlers -->|TTS| NeuralTTS[Neural TTS]
        Handlers -->|UI| Vis[Particle Sphere UI]
    end

    S[AssistantState] --- Core
    S --- Vision Layer
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai/) with `llama3` installed.
- Windows 10/11.
- Webcam and Microphone.

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/aethera.git
   cd aethera/python-client
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up `.env`:
   ```env
   N8N_WEBHOOK_URL=http://localhost:5678/webhook/voice-assistant
   OLLAMA_URL=http://localhost:11434/api/generate
   ```

---

## 🖱️ Gesture Guide
Aethera supports 22+ gestures organized into 4 categories:
- **Assistant Control**: Wake, Stop, Confirm/Deny.
- **Cursor & Navigation**: Air mouse, Scroll, Zoom.
- **OS Control**: Switch Desktops, Maximize/Minimize, Start Menu.
- **Media & System**: Volume, Brightness, Screenshot, Mute.

---

## 🔒 Security & Privacy
- **Local First**: All voice processing (STT/LLM) and vision processing (FaceID/Gestures) happens locally on your machine.
- **Biometric Locking**: Optional "Security Gate" that can lock your Windows workstation if an unauthorized person is detected.
- **Intrusion Logs**: Photos of unauthorized access attempts are stored in `data/intrusions/` and presented to the owner upon return.

---

## 🛠️ Development
Adding a new command is as simple as creating a new file in `handlers/`:

```python
from handlers.base_handler import BaseHandler

class MyNewHandler(BaseHandler):
    INTENT_NAME = "MY_CUSTOM_INTENT"
    
    def handle(self, intent, state, permission_manager):
        # Your logic here
        return TaskResult(True, "Command executed successfully!")
```
