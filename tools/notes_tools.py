import json
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

NOTES_FILE = Path("aethera_notes.json")

@tool
def save_note(title: str, content: str, tags: str = "") -> str:
    """Save a note or piece of information for future reference
    Use when user asks to note something down, save info, or create a reminder note.

    Args:
        title: Short title for the note
        content: Full note content
        tags: Comma-separated tags for categorization
    """

    notes = json.loads(NOTES_FILE.read_text()) if NOTES_FILE.exists() else []
    notes.append({
        "id": len(notes) + 1,
        "title": title,
        "content": content,
        "tags": tags.split(","),
        "created": datetime.now().isoformat(),
    })
    NOTES_FILE.write_text(json.dumps(notes, indent=2))
    return f"Note '{title}' saved."

@tool 
def search_notes(query: str) -> str:
    """Search saved notes by keyword, title, or tag
    Args:
        query: Search term to find in notes
    """

    if not NOTES_FILE.exists():
        return "No notes saved yet."

    notes = json.loads(NOTES_FILE.read_text())
    query_lower = query.lower()
    matches = [
        n for n in notes
        if query_lower in n["title"].lower()
        or query_lower in n["content"].lower()
        or any(query_lower in t for t in n["tags"])
    ]
    if not matches:
        return "No matching notes found."
    
    return "\n\n".join(
        f"[{n['id']}] {n['title']} ({n['created'][:10]})\n{n['content'][:200]}"
        for n in matches
    )

NOTE_TOOLS = [
    save_note,
    search_notes
]