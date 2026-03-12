import sqlite3
from datetime import datetime
from collections import deque

class AetheraMemory:
    """
    Three layer memory system:
        1. Working memory - current conversation turns
        2. Episodic memory - past events stored in SQLite
        3. User profile - persistent preferences and facts
    """

    WORKING_MEMORY_SIZE = 20

    def __init__(self, db_path: str = "aethera_memory.db"):
        self.db_path = db_path
        self._working: deque = deque(maxlen=self.WORKING_MEMORY_SIZE)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    tags TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL         
                )
            """)

        if not self.get_profile("name"):
            self.set_profile("name", "Sir")
            self.set_profile("formality", "formal")

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=True)
    
    # Layer 1 - Working Memory

    def add_turn(self, role: str, content):
        """Add a turn to working memory. Content can be str or list"""
        self._working.append({"role": role, "content": content})

    def get_conversation(self) -> list[dict]:
        return list(self._working)
    
    def clear_working(self):
        self._working.clear()

    # Layer 2 - Episodic Memory

    def remember_episode(self, summary: str, tags: list[str] | None = None):
        ts = datetime.now().isoformat(timespec="seconds")
        tags_str = ",".join(tags) if tags else ""

        with self._conn() as conn:
            conn.execute(
                "INSERT INTO episodes (timestamp, summary, tags) VALUES (?, ?, ?)",
                (ts, summary, tags_str)
            )

    def recall_episodes(self, limit: int = 5) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT timestamp, summary, tags FROM episodes ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"when": r[0], "what": r[1], "tags": r[2]} for r in rows]
    
    def get_episode_summary(self, limit: int = 5) -> str:
        episodes = self.recall_episodes(limit)
        if not episodes:
            return "No previous interactions on record."
        lines = [f"- [{e['when']}] {e['what']}" for e in reversed(episodes)]
        return "\n".join(lines)
    
    # Layer 3 - User Profile

    def set_profile(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO profile (key, value) VALUES (?, ?)",
                (key, value)
            )

    def get_profile(self, key: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM profile WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None
    
    def get_all_profile(self) -> dict:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key, value FROM profile"
            ).fetchall()
        return {r[0]: r[1] for r in rows}
    
    def profile_summary(self) -> str:
        profile = self.get_all_profile()
        if not profile:
            return "No user profile data."
        return "\n".join(f"- {k}: {v}" for k, v in profile.items())