# FILE: hitl/manager.py
"""Orchestrates the HITL workflow end-to-end:
  1. check_and_create(): evaluate trigger rules against a turn's
     decision_context; if any fire, persist a pending task and return it.
  2. pending(): list all pending tasks for the review queue.
  3. review(): apply a human decision and resume.

The agent (chains/hitl_chain.py) calls check_and_create() BEFORE returning
a final answer for any turn that touched a HITL-sensitive action; if a
task is created, the turn returns type="pending_approval" instead of the
normal answer, and the caller must poll /hitl/pending or be notified.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hitl.models import HITLTask
from hitl.store import HITLStore, get_store
from hitl.triggers import TriggerEngine
from utils.logger import get_logger

logger = get_logger("hitl.manager")


class HITLManager:
    def __init__(self, store: HITLStore | None = None, trigger_engine: TriggerEngine | None = None):
        self.store = store or get_store()
        self.trigger_engine = trigger_engine or TriggerEngine()

    def check_and_create(
        self,
        session_id: str,
        decision_context: dict,
        recommendation: str,
        confidence_score: float | None = None,
    ) -> HITLTask | None:
        """Returns a newly created (and persisted) HITLTask if any trigger
        rule fired, else None (turn proceeds normally)."""
        matched = self.trigger_engine.evaluate(decision_context)
        if not matched:
            return None

        severity = self.trigger_engine.highest_severity(matched)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=self.trigger_engine.default_expiry_hours)
        ).isoformat()

        task = HITLTask.new(
            session_id=session_id,
            triggered_rule_ids=[r.id for r in matched],
            severity=severity,
            recommendation=recommendation,
            context=decision_context,
            confidence_score=confidence_score,
            expires_at=expires_at,
        )
        self.store.save(task)
        logger.info(
            "HITL task created task_id=%s session=%s rules=%s severity=%s",
            task.task_id, session_id, task.triggered_rule_ids, severity,
        )
        return task

    def pending(self) -> list[HITLTask]:
        return self.store.list_pending()

    def review(self, task_id: str, decision: str, decided_by: str, comments: str | None) -> HITLTask:
        if decision not in ("approve", "reject"):
            raise ValueError(f"decision must be 'approve' or 'reject', got '{decision}'")

        task = self.store.get(task_id)
        if task is None:
            raise KeyError(f"No HITL task with id '{task_id}'")
        if task.status.value != "pending":
            raise ValueError(f"Task '{task_id}' is already resolved (status={task.status.value})")

        updated = self.store.decide(
            task_id,
            approved=(decision == "approve"),
            decided_by=decided_by,
            comments=comments,
            decided_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("HITL task %s resolved: %s by %s", task_id, decision, decided_by)
        return updated


_manager: HITLManager | None = None


def get_manager() -> HITLManager:
    global _manager
    if _manager is None:
        _manager = HITLManager()
    return _manager