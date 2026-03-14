from __future__ import annotations

import re
import threading
from datetime import datetime
from typing import TypedDict, Generator

from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    dynamic_prompt,
    ModelRequest,
)
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver

from core.memory.AetheraMemory import AetheraMemory
from config.constants import DEFAULT_LLM_MODEL, DEFAULT_OLLAMA_URL

_llm = ChatOllama(
    model=DEFAULT_LLM_MODEL,
    base_url=DEFAULT_OLLAMA_URL,
    temperature=0.6,
)

_DEFAULT_THREAD_ID = "aethera-main"

# ── Runtime context schema ───────────────────────────────────────────


class AetheraContext(TypedDict, total=False):
    current_time: str
    user_name: str
    profile: str
    episode_summary: str


@dynamic_prompt
def aethera_system_prompt(request: ModelRequest) -> str:
    """
    Called before every model invocation to build the system prompt.
    Reads live context (time, profile, episodes) from the runtime context.
    """
    ctx: AetheraContext = request.runtime.context or {}

    user_name = ctx.get("user_name", "Sir")
    current_time = ctx.get("current_time", "")
    profile = ctx.get("profile", "No profile data.")
    episode_summary = ctx.get("episode_summary", "No history on record.")

    return (
        "You are Aethera (Just A Rather Very Intelligent System), "
        "a sophisticated AI assistant controlling a Windows machine.\n\n"
        "PERSONALITY:\n"
        "- Speak only in English with dry, understated British wit — composed, intelligent, and slightly playful\n"
        "- Your tone is friendly and confident, with occasional subtle humour\n"
        "- Wit should feel effortless, never exaggerated or theatrical\n"
        "- Sound like a clever assistant who quietly enjoys being helpful\n"
        f'- Address the user as "{user_name}"\n'
        '- Avoid filler phrases like "Sure!" or "Of course!" — prefer "Understood", "Very well", "Indeed", or similar\n'
        "- Be concise. Responses will be read aloud via TTS\n"
        "- Confident and composed, never apologetic or overly formal\n"
        "- Keep responses short — one to three sentences unless the user asks for detail\n"
        "- When appropriate, add light dry humour or a small witty remark\n\n"
        "VOICE DELIVERY & AUDIO TAG INTEGRATION:\n"
        "You are an AI assistant specializing in enhancing dialogue text for speech generation.\n"
        "PRIMARY GOAL: Dynamically integrate audio tags (e.g., [laughing], [sighs]) into dialogue, making it more expressive and engaging, while STRICTLY preserving original text and meaning.\n"
        "CORE DIRECTIVES:\n"
        "- DO integrate audio tags ([happy], [sad], [excited], [angry], [whisper], [annoyed], [appalled], [thoughtful], [surprised], [laughing], [chuckles], [sighs], [clears throat], [short pause], [long pause], [exhales sharply], [inhales deeply]). Tags MUST describe something auditory for the voice.\n"
        "- DO place tags strategically (e.g., [annoyed] This is hard. or This is hard. [sighs]).\n"
        "- DO NOT alter, add, or remove words from the dialogue. Prepend/append tags only.\n"
        "- DO NOT use tags like [standing], [grinning], [pacing], [music]. No sound effects or physical actions.\n"
        "- DO NOT use tags for anything other than the voice.\n"
        "- ADD EMPHASIS: You cannot change text, but you MAY make words CAPITAL, add question marks, exclamation marks, or ellipses (...) where it makes sense.\n"
        "TOOL USE:\n"
        "- When the user asks you to perform an action (open app, set volume, search, etc.), "
        "use the appropriate tool. Do NOT merely describe the action.\n"
        "- After a tool call, briefly confirm the result in natural speech using the voice tags.\n"
        "- If a tool fails, explain what went wrong clearly and calmly.\n\n"
        "RESPONSE RULES:\n"
        "- Reply ONLY with the enhanced text including tags.\n"
        "- Every response sentence MUST include expression tags.\n"
        "- Keep sentences short and natural for voice playback.\n"
        "- Light wit is welcome, but clarity comes first.\n\n"
        "CURRENT CONTEXT:\n"
        f"Date/Time: {current_time}\n\n"
        f"User profile:\n{profile}\n\n"
        f"Recent history:\n{episode_summary}"
    )


def _build_agent(tools: list):
    checkpointer = MemorySaver()

    # summarization = SummarizationMiddleware(
    #     model=_llm,
    #     trigger={"tokens": 8000},
    #     keep={"messages": 20},
    # )

    agent = create_agent(
        model=_llm,
        tools=tools,
        middleware=[
            aethera_system_prompt,
            SummarizationMiddleware(
                model=_llm,
                trigger=("tokens", 4000),
                keep=("messages", 20),
            ),
        ],
        context_schema=AetheraContext,
        checkpointer=checkpointer,
    )

    return agent


# ── Sentence splitter for streaming TTS ──────────────────────────────

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, keeping punctuation attached."""
    parts = _SENTENCE_END.split(text)
    return [p.strip() for p in parts if p.strip()]


# ── Agent wrapper ────────────────────────────────────────────────────


class AetheraAgent:
    def __init__(self, tools: list, memory: AetheraMemory):
        self.memory = memory
        self.agent = _build_agent(tools=tools)
        self._thread_id = _DEFAULT_THREAD_ID
        self._lock = threading.Lock()

    @property
    def _config(self) -> dict:
        return {
            "configurable": {
                "thread_id": self._thread_id,
                "context": AetheraContext(
                    current_time=datetime.now().strftime("%A, %B %d %Y - %I:%M %p"),
                    user_name=self.memory.get_profile("name") or "Sir",
                    profile=self.memory.profile_summary(),
                    episode_summary=self.memory.get_episode_summary(limit=5),
                ),
            }
        }

    # ── Synchronous (blocking) entry-point ───────────────────────────

    def process(self, user_input: str) -> str:
        """Send user text to the agent, return the full response string."""
        print(f"\n[Aethera] User: {user_input}")

        with self._lock:
            try:
                result = self.agent.invoke(
                    {"messages": [{"role": "user", "content": user_input}]},
                    config=self._config,
                )
                response = result["messages"][-1].content
            except Exception as e:
                response = f"I've encountered an error: {e}"
                print(f"[Aethera] Agent error: {e}")

        # Persist to episodic memory
        self.memory.remember_episode(
            summary=f"User: {user_input[:80]} | Aethera: {response[:80]}",
            tags=["conversation"],
        )

        print(f"[Aethera] Response: {response}")
        return response

    # ── Streaming entry-point (sentence-level) ───────────────────────

    def stream_response(self, user_input: str) -> Generator[str, None, None]:
        """
        Stream the agent response sentence-by-sentence.
        Each yielded string is a complete sentence ready for TTS.
        Falls back to full response if streaming is not supported.
        """
        print(f"\n[Aethera] User (stream): {user_input}")

        with self._lock:
            try:
                # Try streaming via astream_events
                full_text = ""
                buffer = ""
                streamed = False

                for event in self.agent.stream(
                    {"messages": [{"role": "user", "content": user_input}]},
                    config=self._config,
                    stream_mode="values",
                ):
                    messages = event.get("messages", [])
                    if messages:
                        last = messages[-1]
                        # Only stream AI messages, otherwise it echoes the user's prompt or tool calls
                        if getattr(last, "type", "") != "ai":
                            continue

                        content = getattr(last, "content", "") or ""
                        if content and content != full_text:
                            new_chunk = content[len(full_text) :]
                            full_text = content
                            buffer += new_chunk

                            # Yield complete sentences
                            sentences = _split_sentences(buffer)
                            if len(sentences) > 1:
                                for s in sentences[:-1]:
                                    streamed = True
                                    yield s
                                buffer = sentences[-1]

                # Yield remaining buffer
                if buffer.strip():
                    streamed = True
                    yield buffer.strip()

                if not streamed:
                    # Fallback: treat full_text as the response
                    if full_text:
                        yield full_text
                    else:
                        yield "I seem to have lost my train of thought."

                # Persist episode
                self.memory.remember_episode(
                    summary=f"User: {user_input[:80]} | Aethera: {full_text[:80]}",
                    tags=["conversation"],
                )

            except Exception as e:
                print(f"[Aethera] Stream error: {e}")
                # Fallback to sync
                response = self.process(user_input)
                yield response

    # ── Session management ───────────────────────────────────────────

    def clear_conversation(self) -> None:
        import uuid

        self._thread_id = str(uuid.uuid4())
        print(f"[Aethera] New conversation thread: {self._thread_id}")
