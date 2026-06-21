import sqlite3
from datetime import datetime


class MemoryStore:

    def __init__(self, db_path="memory.db", max_turns=10):
        self.db_path = db_path
        self.max_turns = max_turns

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                user_message TEXT,
                assistant_message TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    # -------------------------
    # ADD MEMORY
    # -------------------------
    def add(self, session_id: str, user: str, assistant: str):

        self.cursor.execute("""
            INSERT INTO chat_memory (session_id, user_message, assistant_message, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, user, assistant, datetime.utcnow().isoformat()))

        self.conn.commit()

    # -------------------------
    # GET LAST N MESSAGES
    # -------------------------
    def get(self, session_id: str):

        self.cursor.execute("""
            SELECT user_message, assistant_message
            FROM chat_memory
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (session_id, self.max_turns))

        rows = self.cursor.fetchall()

        return [
            {"user": r[0], "assistant": r[1]}
            for r in reversed(rows)
        ]

    # -------------------------
    # CLEAR SESSION MEMORY
    # -------------------------
    def clear(self, session_id: str):

        self.cursor.execute("""
            DELETE FROM chat_memory
            WHERE session_id = ?
        """, (session_id,))

        self.conn.commit()