# FILE: hitl/store.py
"""SQLite-backed persistent store for HITL tasks -- satisfies the NFR that
"HITL approval state persists across container restarts (stored in
database or persistent volume)". Uses stdlib sqlite3 only, so it has no
extra runtime dependency and the DB file just needs to sit on a mounted
volume in docker-compose.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

from hitl.models import HITLTask, HITLStatus

DEFAULT_DB_PATH = "data/hitl_tasks.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hitl_tasks (
    task_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    triggered_rule_ids TEXT NOT NULL,
    severity TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    context TEXT NOT NULL,
    confidence_score REAL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    decided_at TEXT,
    decided_by TEXT,
    decision_comments TEXT
);
CREATE INDEX IF NOT EXISTS idx_hitl_status ON hitl_tasks(status);
CREATE INDEX IF NOT EXISTS idx_hitl_session ON hitl_tasks(session_id);
"""


class HITLStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, task: HITLTask) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO hitl_tasks
                   (task_id, session_id, triggered_rule_ids, severity, recommendation,
                    context, confidence_score, status, created_at, expires_at,
                    decided_at, decided_by, decision_comments)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                     status=excluded.status,
                     decided_at=excluded.decided_at,
                     decided_by=excluded.decided_by,
                     decision_comments=excluded.decision_comments""",
                (
                    task.task_id, task.session_id, json.dumps(task.triggered_rule_ids),
                    task.severity, task.recommendation, json.dumps(task.context),
                    task.confidence_score, task.status.value if isinstance(task.status, HITLStatus) else task.status,
                    task.created_at, task.expires_at, task.decided_at, task.decided_by,
                    task.decision_comments,
                ),
            )

    def get(self, task_id: str) -> HITLTask | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM hitl_tasks WHERE task_id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_pending(self) -> list[HITLTask]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hitl_tasks WHERE status = ? ORDER BY created_at ASC",
                (HITLStatus.PENDING.value,),
            ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def list_by_session(self, session_id: str) -> list[HITLTask]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hitl_tasks WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def decide(self, task_id: str, approved: bool, decided_by: str, comments: str | None, decided_at: str) -> HITLTask | None:
        task = self.get(task_id)
        if task is None:
            return None
        task.status = HITLStatus.APPROVED if approved else HITLStatus.REJECTED
        task.decided_at = decided_at
        task.decided_by = decided_by
        task.decision_comments = comments
        self.save(task)
        return task

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> HITLTask:
        return HITLTask(
            task_id=row["task_id"],
            session_id=row["session_id"],
            triggered_rule_ids=json.loads(row["triggered_rule_ids"]),
            severity=row["severity"],
            recommendation=row["recommendation"],
            context=json.loads(row["context"]),
            confidence_score=row["confidence_score"],
            status=HITLStatus(row["status"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            decided_at=row["decided_at"],
            decided_by=row["decided_by"],
            decision_comments=row["decision_comments"],
        )


_store: HITLStore | None = None


def get_store() -> HITLStore:
    global _store
    if _store is None:
        import os
        os.makedirs("data", exist_ok=True)
        _store = HITLStore()
    return _store