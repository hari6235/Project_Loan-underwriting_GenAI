# FILE: memory/memory_store.py
"""SQLite-backed conversation memory. This module was referenced by
api/routes.py (`from memory.memory_store import MemoryStore`) but was
missing from the project entirely -- api/routes.py would have failed at
import time. Implemented here against the EXISTING memory.db schema
(chat_memory: id, session_id, user_message, assistant_message, timestamp)
so it's compatible with the data already in that file rather than
requiring a migration.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DEFAULT_DB_PATH = "memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_message TEXT,
    assistant_message TEXT,
    timestamp TEXT
)
"""


class MemoryStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH, max_turns: int = 10):
        self.db_path = db_path
        self.max_turns = max_turns
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, session_id: str, user_message: str, assistant_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_memory (session_id, user_message, assistant_message, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (session_id, user_message, assistant_message, datetime.now(timezone.utc).isoformat()),
            )

    def get(self, session_id: str) -> list[dict]:
        """Returns the last `max_turns` turns for this session, oldest
        first (the order core/chain.py's history-formatting expects)."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT user_message, assistant_message FROM chat_memory "
                "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, self.max_turns),
            )
            rows = cur.fetchall()
        rows.reverse()
        return [{"user": u, "assistant": a} for u, a in rows]

    def clear(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chat_memory WHERE session_id = ?", (session_id,))