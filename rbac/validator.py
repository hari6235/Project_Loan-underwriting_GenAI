# FILE: rbac/validator.py
"""Post-retrieval validator: a mandatory SECOND check applied AFTER
reranking, so a restricted chunk that somehow survives to the reranked
top-k (e.g. reintroduced by a cache, or via a code path that forgot to
apply the pre-retrieval filter) is caught before it ever reaches the LLM
prompt or the user. This is defense in depth, not redundant -- the "Role
leakage through re-ranker" pitfall exists precisely because teams assume
the pre-retrieval filter is sufficient on its own.
"""
from __future__ import annotations

from rbac.role_registry import RoleRegistry, get_role_registry


class RoleLeakageError(Exception):
    """Raised when a restricted chunk is found in a result set that has
    already passed through the pre-retrieval filter -- this should never
    happen in correct operation, so it is treated as a hard failure, not
    silently dropped, so the underlying bug gets surfaced and fixed."""


def validate_no_leakage(
    role_name: str,
    chunks: list[dict],
    registry: RoleRegistry = None,
    raise_on_leak: bool = True,
) -> list[dict]:
    """Returns `chunks` filtered to only those the role is permitted to
    see. If any restricted chunk was present, either raises
    RoleLeakageError (raise_on_leak=True, the default -- correct for
    production, since a leak indicates a bug elsewhere) or silently drops
    them and returns the clean list (raise_on_leak=False -- useful for a
    "sanitize and continue" path where availability matters more, e.g. a
    non-critical background job)."""
    registry = registry or get_role_registry()
    role = registry.get(role_name)

    clean = []
    leaked = []
    for chunk in chunks:
        doc_type = chunk.get("metadata", {}).get("doc_type")
        if role.permits(doc_type):
            clean.append(chunk)
        else:
            leaked.append(chunk)

    if leaked and raise_on_leak:
        leaked_types = sorted({c.get("metadata", {}).get("doc_type") for c in leaked})
        raise RoleLeakageError(
            f"Role '{role_name}' retrieved {len(leaked)} chunk(s) of restricted "
            f"doc_type(s) {leaked_types} -- pre-retrieval filter did not fully apply."
        )

    return clean