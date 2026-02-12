from faster_whisper import WhisperModel
from flask import Flask, request, jsonify
import tempfile

app = Flask(__name__)
model = WhisperModel("medium.en", device='cuda')

@app.route("/transcribe", methods=["POST"])
def transcribe():
    audio = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False) as f:
        audio.save(f.name)
        segments, _ = model.transcribe(f.name)
    
    text = " ".join(seg.text for seg in segments)
    return jsonify({"text": text})

app.run(port=9000)