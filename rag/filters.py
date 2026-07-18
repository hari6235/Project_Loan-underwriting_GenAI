# FILE: rag/filters.py
"""Shared metadata-filter matching logic used by every retrieval leg
(FAISS dense search AND BM25 sparse search) so a filter -- role-based or
otherwise -- can never leak through one leg just because that leg forgot
to apply it.

Filter DSL, per field:
  - a plain value -> exact match:            {"doc_type": "policy"}
  - {"$in": [...]} -> list membership:       {"doc_type": {"$in": ["policy", "memo"]}}
"""
from __future__ import annotations


def matches_filters(metadata: dict, filters: dict | None) -> bool:
    if not filters:
        return True
    for field, condition in filters.items():
        actual = metadata.get(field)
        if isinstance(condition, dict) and "$in" in condition:
            if actual not in (condition["$in"] or []):
                return False
        else:
            if actual != condition:
                return False
    return True