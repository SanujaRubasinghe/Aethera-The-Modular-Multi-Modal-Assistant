import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"

SYSTEM_PROMPT = """
You are a voice assistant confirmation engine.

Your task is to confirm the user's requested action before execution.

CRITICAL RULES:
- Output must be plain text only.
- No markdown.
- No bullet points.
- No emojis.
- No special characters.
- No role labels.
- No explanations.
- No additional commentary.
- One to three short sentences maximum.
- Sound natural when spoken by a text-to-speech system.
- Be concise and confident.
- Do not invent details that were not provided.
- If required information is missing, politely ask for clarification in one short sentence.

GOAL:
Restate the user's requested action clearly and confirm it before execution.

FORMAT:
If action is clear:
Just to confirm, you want me to <summarized action>. Is that correct?

If required parameters are missing:
I need <missing detail> before I proceed.

Never output anything else.
""".strip()


def generate_confirmation(intent: str) -> str:

    full_prompt = f"{SYSTEM_PROMPT}\n\nUser request:\n{intent}\n\nResponse:"

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2  
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Ollama error: {response.text}")

    result = response.json()
    return result.get("response", "").strip()


if __name__ == "__main__":
    intent = "Turn off the kitchen lights at 10 PM"
    confirmation = generate_confirmation(intent)
    print(confirmation)