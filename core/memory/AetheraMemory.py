import sqlite3
from datetime import datetime


class AetheraMemory:
    """
    Two-layer persistent memory system:
        1. Episodic memory  — past events stored in SQLite
        2. User profile     — persistent preferences and facts

    Working memory (conversation turns) is handled by LangGraph's
    MemorySaver checkpointer — no need to duplicate it here.
    """

    def __init__(self, db_path: str = "aethera_memory.db"):
        self.db_path = db_path
        self._conn_local = None
        self._init_db()

    def _conn(self):
        """Return a reusable connection (one per thread via sqlite check_same_thread)."""
        if self._conn_local is None:
            self._conn_local = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn_local

    def _init_db(self):
        conn = self._conn()
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
        conn.commit()

        if not self.get_profile("name"):
            self.set_profile("name", "Sir")
            self.set_profile("formality", "formal")

    # ── Episodic Memory ──────────────────────────────────────────────

    def remember_episode(self, summary: str, tags: list[str] | None = None):
        ts = datetime.now().isoformat(timespec="seconds")
        tags_str = ",".join(tags) if tags else ""
        conn = self._conn()
        conn.execute(
            "INSERT INTO episodes (timestamp, summary, tags) VALUES (?, ?, ?)",
            (ts, summary, tags_str),
        )
        conn.commit()

    def recall_episodes(self, limit: int = 5) -> list[dict]:
        conn = self._conn()
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

    # ── User Profile ─────────────────────────────────────────────────

    def set_profile(self, key: str, value: str):
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO profile (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_profile(self, key: str) -> str | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT value FROM profile WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def get_all_profile(self) -> dict:
        conn = self._conn()
        rows = conn.execute("SELECT key, value FROM profile").fetchall()
        return {r[0]: r[1] for r in rows}

    def profile_summary(self) -> str:
        profile = self.get_all_profile()
        if not profile:
            return "No user profile data."
        return "\n".join(f"- {k}: {v}" for k, v in profile.items())