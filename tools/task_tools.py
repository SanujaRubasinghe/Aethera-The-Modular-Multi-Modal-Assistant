from datetime import datetime
from langchain_core.tools import tool
from pathlib import Path
import json

@tool
def manage_tasks(action: str, title: str = "",
                 priority: str = "normal", task_id: int = 0) -> str:
    """Manage a personal task list — add, list, complete, or delete tasks.

    Args:
        action:   'add', 'list', 'complete', 'delete', 'pending'
        title:    Task description (for add)
        priority: 'low', 'normal', 'high', 'urgent'
        task_id:  ID of task to complete/delete
    """
    TASKS_FILE = Path("aethera_tasks.json")
    tasks = json.loads(TASKS_FILE.read_text()) if TASKS_FILE.exists() else []

    if action == "add":
        tasks.append({
            "id": len(tasks) + 1,
            "title": title,
            "priority": priority,
            "done": False,
            "created": datetime.now().isoformat(),
        })
        TASKS_FILE.write_text(json.dumps(tasks, indent=2))
        return f"Task added: '{title}' [{priority}]"

    elif action in ("list", "pending"):
        filtered = [t for t in tasks if not t["done"]] if action == "pending" else tasks
        if not filtered:
            return "No tasks."
        return "\n".join(
            f"[{t['id']}] {'✓' if t['done'] else '○'} [{t['priority']}] {t['title']}"
            for t in filtered
        )

    elif action == "complete":
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
        TASKS_FILE.write_text(json.dumps(tasks, indent=2))
        return f"Task {task_id} marked complete."
    

TASK_TOOLS = [
    manage_tasks
]