# FILE: hitl/models.py
"""Data models for the HITL workflow. Plain dataclasses (not pydantic) so
this module has zero framework dependency and is trivially unit-testable;
api/routes.py converts to/from pydantic at the API boundary."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class HITLStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class HITLTask:
    task_id: str
    session_id: str
    triggered_rule_ids: list[str]
    severity: str                       # highest severity among triggered rules
    recommendation: str                 # the AI's proposed answer/action
    context: dict                       # retrieved chunks, tool outputs, reasoning trace
    confidence_score: float | None
    status: HITLStatus = HITLStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None
    decision_comments: str | None = None

    @staticmethod
    def new(
        session_id: str,
        triggered_rule_ids: list[str],
        severity: str,
        recommendation: str,
        context: dict,
        confidence_score: float | None = None,
        expires_at: str | None = None,
    ) -> "HITLTask":
        return HITLTask(
            task_id=str(uuid.uuid4()),
            session_id=session_id,
            triggered_rule_ids=triggered_rule_ids,
            severity=severity,
            recommendation=recommendation,
            context=context,
            confidence_score=confidence_score,
            expires_at=expires_at,
        )