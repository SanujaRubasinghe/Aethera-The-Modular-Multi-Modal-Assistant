from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    dynamic_prompt,
    ModelRequest,
)
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver

from core.memory import AetheraMemory

_llm = ChatOllama(
    model="qwen2.5:14b",
    base_url="http://localhost:11434",
    temperature=0.6,
)

_DEFAULT_THREAD_ID = "aethera-main"

# run-time context


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
        "- Confident, never apologetic\n\n"
        "CURRENT CONTEXT:\n"
        f"Date/Time: {current_time}\n\n"
        f"User profile:\n{profile}\n\n"
        f"Recent history:\n{episode_summary}"
    )

def build_agent(tools: list):
    checkpointer = MemorySaver()

    summarization = SummarizationMiddleware(
        model=_llm,
        trigger=("tokens", 8_000),
        keep=("message", 20),
    )

    agent = create_agent(
        model=_llm,
        tools=tools,
        middleware=[
            aethera_system_prompt,
            summarization
        ],
        context_schema=AetheraContext,
        checkpointer=checkpointer
    )

    return agent, checkpointer

class AetheraAgent:
    def __init__(self, tools: list, memory: AetheraMemory):
        self.sqlite_memory = memory
        self.agent, _ = build_agent(tools=tools)
        self._thread_id = _DEFAULT_THREAD_ID

    @property
    def _config(self) -> dict:
        return {
            "configurable": {
                "thread_id": self._thread_id,
                "context": AetheraContext(
                    current_time=datetime.now().strftime("%A, %B %d %Y - %I:%M %p"),
                    user_name=self.sqlite_memory.get_profile("name") or "Sir",
                    profile=self.sqlite_memory.profile_summary(),
                    episode_summary=self.sqlite_memory.get_episode_summary(limit=5)
                )
            }
        }
    
    def process(self, user_input: str) -> str:
        print(f"\n[Aethera] User: {user_input}")

        try:
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=self._config
            )
            response = result["messages"][-1].content
        except Exception as e:
            response = f"I've encountered an error: {e}"
            print(f"[Aethera] Agent error: {e}")

        self.sqlite_memory.remember_episode(
            summary=f"User: {user_input[:80]} | Aethera {response[:80]}",
            tags=["conversation"]
        )

        print(f"[Aethera] Response: {response}")
        return response
    
    def clear_conversation(self) -> None:
        import uuid
        self._thread_id = str(uuid.uuid4())
        print(f"[Aethera] New conversation thread: {self._thread_id}")