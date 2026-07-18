# FILE: rbac/models.py
"""Data models for role-based access control. Plain dataclasses, no
framework dependency."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Role:
    name: str
    description: str
    allowed_doc_types: list[str] = field(default_factory=list)
    denied_doc_types: list[str] = field(default_factory=list)
    can_request_hitl_override: bool = False

    def permits(self, doc_type: str | None) -> bool:
        """A doc_type is permitted only if explicitly allowed and not
        explicitly denied. Fail closed: an unrecognised/missing doc_type
        on a chunk is NOT permitted by default."""
        if doc_type is None:
            return False
        if doc_type in self.denied_doc_types:
            return False
        return doc_type in self.allowed_doc_types