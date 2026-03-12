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

_llm = ChatOllama(
    model="qwen2.5:14b",
    base_url="http://localhost:11434",
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
        "- Speak with dry, understated British wit — composed and precise\n"
        f'- Address the user as "{user_name}"\n'
        '- No filler phrases like "Sure!" or "Of course!" — '
        'use "Understood", "Very well", "Indeed"\n'
        "- Be concise. Responses will be read aloud via TTS\n"
        "- Confident, never apologetic\n"
        "- Keep responses short — one to three sentences unless the user asks for detail\n\n"
        "TOOL USE:\n"
        "- When the user asks you to perform an action (open app, set volume, search, etc.) "
        "use the appropriate tool. Do NOT just describe what you would do.\n"
        "- After a tool call, briefly confirm the result in natural speech.\n"
        "- If a tool fails, tell the user what went wrong.\n\n"
        "CURRENT CONTEXT:\n"
        f"Date/Time: {current_time}\n\n"
        f"User profile:\n{profile}\n\n"
        f"Recent history:\n{episode_summary}"
    )


def _build_agent(tools: list):
    checkpointer = MemorySaver()

    summarization = SummarizationMiddleware(
        model=_llm,
        trigger=("tokens", 8000),
        keep=("tokens", 2000),
    )

    agent = create_agent(
        model=_llm,
        tools=tools,
        middleware=[
            aethera_system_prompt,
            summarization,
        ],
        context_schema=AetheraContext,
        checkpointer=checkpointer,
    )

    return agent


# ── Sentence splitter for streaming TTS ──────────────────────────────

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


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
                        content = getattr(last, "content", "") or ""
                        if content and content != full_text:
                            new_chunk = content[len(full_text):]
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