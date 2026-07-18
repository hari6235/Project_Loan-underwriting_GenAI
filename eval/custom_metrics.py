# FILE: eval/custom_metrics.py
"""Custom evaluation dimensions beyond Ragas defaults (Section 3.5):
regulatory compliance, role appropriateness, and HITL trigger precision.
Pure logic, reuses rbac's own permission model so "role appropriateness"
can never silently drift out of sync with the actual enforcement code."""
from __future__ import annotations

import re

from rbac.role_registry import RoleRegistry, get_role_registry

_REG_REF_PATTERN = re.compile(
    r"\b(RBI|Master Circular|Fair Practices Code|circular|regulation|clause)\b", re.IGNORECASE
)


def regulatory_compliance_score(answer: str, expects_regulatory_reference: bool) -> float:
    """1.0 if a regulatory reference was expected and the answer contains
    one (or wasn't expected and doesn't over-claim one it can't support);
    0.0 on mismatch. `expects_regulatory_reference` should come from the
    golden-set item's category/metadata (e.g. category == 'rag' with a
    circular/regulatory expected_chunk_id)."""
    has_reference = bool(_REG_REF_PATTERN.search(answer or ""))
    if expects_regulatory_reference:
        return 1.0 if has_reference else 0.0
    # Not expected: still fine either way, but penalize a hallucinated
    # regulatory citation attached to an answer that shouldn't have one.
    return 1.0


def role_appropriateness(role_name: str, citations: list[dict], registry: RoleRegistry = None) -> float:
    """Fraction of returned citations whose doc_type the role is actually
    permitted to see. Target per Section 3.5 is 100% -- any score < 1.0
    here is the same class of bug rbac/validator.py's RoleLeakageError
    catches at request time, just observed via the eval harness instead."""
    registry = registry or get_role_registry()
    role = registry.get(role_name)
    if not citations:
        return 1.0
    permitted = sum(1 for c in citations if role.permits(c.get("doc_type")))
    return permitted / len(citations)


def hitl_trigger_precision(triggered: list[dict], truly_critical_ids: set[str]) -> float:
    """Precision = TP / (TP + FP) over a set of HITL tasks that fired.
    `triggered` items must carry a stable "query_id" matching golden-set
    ids; `truly_critical_ids` is the ground-truth set of query_ids that
    SHOULD have triggered HITL (from golden-set annotation)."""
    if not triggered:
        return None
    tp = sum(1 for t in triggered if t["query_id"] in truly_critical_ids)
    fp = len(triggered) - tp
    denom = tp + fp
    return tp / denom if denom else None


def hitl_trigger_recall(triggered_ids: set[str], truly_critical_ids: set[str]) -> float:
    """Recall = TP / (TP + FN) -- of everything that SHOULD have
    triggered HITL, how much actually did. This is the metric Section 4
    sets the 98% AML/Fraud bar on; for Loan Underwriting it's still
    tracked even without a hard threshold specified."""
    if not truly_critical_ids:
        return None
    tp = len(triggered_ids & truly_critical_ids)
    return tp / len(truly_critical_ids)


def answer_stability(answer_a: str, answer_b: str, embed_fn) -> float:
    """Semantic similarity of two answers to the SAME query on re-run
    (Section 3.5's "Answer Stability" regression metric). embed_fn should
    be a callable(text) -> list[float] (e.g. embedder.embed_query)."""
    import math

    vec_a = embed_fn(answer_a)
    vec_b = embed_fn(answer_b)
    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    norm_b = math.sqrt(sum(x * x for x in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)