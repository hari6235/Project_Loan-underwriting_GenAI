# FILE: rbac/audit.py
"""Append-only JSON-lines audit log of every role-filtered retrieval, per
the deliverable requirement ("audit logging of all role-filtered
retrievals"). Deliberately file-based and dependency-free so it works
identically in tests and in the containerised deployment (mount the file
path on a persistent volume in docker-compose)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

DEFAULT_AUDIT_LOG_PATH = "logs/rbac_audit.jsonl"


def log_retrieval(
    role_name: str,
    session_id: str,
    query: str,
    allowed_doc_types: list[str],
    returned_chunk_ids: list[str],
    leaked_and_dropped_chunk_ids: list[str] | None = None,
    log_path: str = DEFAULT_AUDIT_LOG_PATH,
) -> dict:
    """Writes one audit record and returns it. leaked_and_dropped_chunk_ids
    should be non-empty ONLY if rbac/validator.py caught something the
    pre-retrieval filter missed -- any such record is a signal worth
    alerting on, not routine noise."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role_name,
        "session_id": session_id,
        "query_preview": query[:200],
        "allowed_doc_types": allowed_doc_types,
        "returned_chunk_ids": returned_chunk_ids,
        "returned_count": len(returned_chunk_ids),
        "leaked_and_dropped_chunk_ids": leaked_and_dropped_chunk_ids or [],
    }
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_audit_log(log_path: str = DEFAULT_AUDIT_LOG_PATH, limit: int = 100) -> list[dict]:
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r") as f:
        lines = f.readlines()[-limit:]
    return [json.loads(line) for line in lines if line.strip()]