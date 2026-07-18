# FILE: rbac/filter.py
"""Pre-retrieval role filter: injects role-based metadata constraints
INTO the retrieval query (before hybrid_search runs), rather than
retrieving everything and filtering afterward. This is what keeps the
NFR's <200ms overhead achievable -- it narrows the candidate set at the
vector-store/BM25 level instead of doing a second pass over a larger
result set. See rbac/validator.py for the mandatory second, post-retrieval
check (defense in depth against a re-ranker or cache reintroducing a
restricted chunk -- see the "Role leakage through re-ranker" pitfall)."""
from __future__ import annotations

from rbac.models import Role
from rbac.role_registry import RoleRegistry, get_role_registry


def build_role_filter(role_name: str, registry: RoleRegistry | None = None) -> dict:
    """Returns a metadata filter dict (doc_type: {"$in": [...]}) suitable
    for merging into the `filters` argument already accepted by
    hybrid_search()/vector_store.search(). Callers should merge this with
    any caller-supplied filters via merge_filters(), never bypass it."""
    registry = registry or get_role_registry()
    role: Role = registry.get(role_name)

    allowed = [dt for dt in role.allowed_doc_types if dt not in role.denied_doc_types]
    # Fail closed: a role with no allowed doc_types gets a filter that
    # matches nothing, not a filter that's silently ignored.
    return {"doc_type": {"$in": allowed}}


def merge_filters(role_filter: dict, caller_filters: dict | None) -> dict:
    """Merges the mandatory role filter with any additional caller-supplied
    filters (e.g. jurisdiction). The role filter's doc_type constraint
    always wins if the caller also specified doc_type -- a caller cannot
    widen their own access by passing a broader doc_type filter."""
    merged = dict(caller_filters or {})
    merged["doc_type"] = role_filter["doc_type"]
    return merged