"""
LangChain @tool wrappers for memory operations.

Lets the agent store and recall user preferences / profile data by reasoning.
"""
from __future__ import annotations

from langchain_core.tools import tool

# Injected at boot-time by VoiceAssistant
_memory = None  # type: ignore


def set_memory(memory):
    """Called once during startup to inject the AetheraMemory instance."""
    global _memory
    _memory = memory


@tool
def remember_user_preference(key: str, value: str) -> str:
    """Store a user preference or fact. Examples: name, favorite color, formality level."""
    if not _memory:
        return "Memory system not available."
    _memory.set_profile(key, value)
    return f"Got it — I'll remember that your {key} is {value}."


@tool
def recall_user_preference(key: str) -> str:
    """Recall a stored user preference by key."""
    if not _memory:
        return "Memory system not available."
    value = _memory.get_profile(key)
    if value:
        return f"Your {key} is {value}."
    return f"I don't have anything stored for '{key}'."


MEMORY_TOOLS = [
    remember_user_preference,
    recall_user_preference,
]
