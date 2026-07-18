# FILE: eval/regression_suite.py
"""Automated regression suite (Section 3.5): runs the golden set through
the LIVE system on every deployment and checks results against the
Section 3.5/4 acceptance-threshold table, producing a pass/fail per
metric plus an overall pass rate. Also computes the two metrics
eval/run_eval.py's aggregate result doesn't already expose:
citation_coverage and role_filter_leakage_rate (both required by the
Section 3.5 table and the 0%-leakage sign-off criterion).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from eval.run_eval import load_golden_set, retrieve_fn, answer_fn, run_full_eval
from eval.custom_metrics import regulatory_compliance_score, role_appropriateness, answer_stability
from rbac.role_registry import get_role_registry
from rbac.validator import validate_no_leakage, RoleLeakageError

ACCEPTANCE_THRESHOLDS = {
    "hit_rate_at_5": 0.85,
    "mrr": 0.65,
    "faithfulness": 0.90,
    "answer_correctness": 0.80,
    "llm_judge_avg": 4.0,
    "citation_coverage": 1.0,
    "role_filter_leakage_rate": 0.0,   # lower is better -- see _passes()
    "role_appropriateness": 1.0,       # Section 3.5 table: target 100%
}

# Tracked (reported in every run) but with no fixed pass/fail threshold in
# Section 3.5's table -- these still feed the trend dashboard and
# comparator, just without a hard gate on overall_pass.
UNGATED_METRICS = {"regulatory_compliance_score", "answer_stability"}


def _passes(metric: str, value: float | None) -> bool | None:
    if value is None:
        return None
    threshold = ACCEPTANCE_THRESHOLDS[metric]
    if metric == "role_filter_leakage_rate":
        return value <= threshold
    return value >= threshold


def _citation_coverage(golden_set: list[dict]) -> dict:
    """Fraction of RAG/hybrid answers that carry at least one citation --
    Section 2's hard requirement is "every answer contains at least one
    citation; no uncited factual claims." Refusal-test items (empty
    expected_chunk_ids) are excluded: a correct refusal has no citations
    by design and shouldn't count against coverage."""
    checked = [g for g in golden_set if g.get("eval_bucket") in ("rag", "hybrid") and g.get("expected_chunk_ids")]
    if not checked:
        return {"value": None, "n": 0}
    covered = 0
    for item in checked:
        result = answer_fn(item)
        if result.get("citations"):
            covered += 1
    return {"value": covered / len(checked), "n": len(checked)}


def _role_filter_leakage_rate(golden_set: list[dict]) -> dict:
    """Runs retrieve_fn (the exact path /chat and /retrieve use) for every
    role_boundary_test item and checks the returned chunks against that
    item's assigned role via the SAME validator used at request time. A
    leak here means the pre-retrieval filter failed for a case explicitly
    designed to probe it."""
    registry = get_role_registry()
    boundary_items = [g for g in golden_set if g.get("category") == "role_boundary_test"]
    if not boundary_items:
        return {"value": None, "n": 0}

    leaked = 0
    for item in boundary_items:
        role = item.get("role", "junior_analyst")
        retrieved = retrieve_fn(item)  # already passed through validate_no_leakage(raise_on_leak=False)
        try:
            validate_no_leakage(role, retrieved, registry, raise_on_leak=True)
        except RoleLeakageError:
            leaked += 1
    return {"value": leaked / len(boundary_items), "n": len(boundary_items)}


def _role_appropriateness_avg(golden_set: list[dict]) -> dict:
    """Average fraction of returned citations each item's assigned role is
    actually permitted to see, across every RAG/hybrid item (not just the
    dedicated role_boundary_test items) -- Section 3.5's "Role
    Appropriateness" custom dimension, target 100%."""
    registry = get_role_registry()
    checked = [g for g in golden_set if g.get("eval_bucket") in ("rag", "hybrid")]
    if not checked:
        return {"value": None, "n": 0}
    scores = []
    for item in checked:
        role = item.get("role", "junior_analyst")
        result = answer_fn(item)
        scores.append(role_appropriateness(role, result.get("citations", []), registry))
    return {"value": sum(scores) / len(scores), "n": len(scores)}


def _regulatory_compliance_avg(golden_set: list[dict]) -> dict:
    """Average regulatory_compliance_score over items whose expected
    answer depends on a circular/regulatory source (category=='regulatory'
    or an expected_chunk_id containing 'circular')."""
    checked = [
        g for g in golden_set
        if g.get("eval_bucket") in ("rag", "hybrid")
        and (g.get("category") == "regulatory" or any("circular" in cid for cid in g.get("expected_chunk_ids", [])))
    ]
    if not checked:
        return {"value": None, "n": 0}
    scores = []
    for item in checked:
        result = answer_fn(item)
        scores.append(regulatory_compliance_score(result.get("response", ""), expects_regulatory_reference=True))
    return {"value": sum(scores) / len(scores), "n": len(scores)}


def _answer_stability_avg(golden_set: list[dict], sample_size: int = 5) -> dict:
    """Re-runs a sample of RAG/hybrid items twice and measures semantic
    similarity between the two answers (Section 3.5's "Answer Stability"
    regression metric). Sampled rather than run over the full set since
    this doubles the LLM calls for whatever it covers."""
    from rag.state import embedder

    checked = [g for g in golden_set if g.get("eval_bucket") in ("rag", "hybrid")][:sample_size]
    if not checked:
        return {"value": None, "n": 0}
    scores = []
    for item in checked:
        answer_a = answer_fn(item).get("response", "")
        answer_b = answer_fn(item).get("response", "")
        scores.append(answer_stability(answer_a, answer_b, embedder.embed_query))
    return {"value": sum(scores) / len(scores), "n": len(scores)}


def run_regression_suite() -> dict:
    raw = run_full_eval()
    golden_set = load_golden_set()

    intrinsic = raw.get("intrinsic", {}) or {}
    extrinsic = raw.get("extrinsic", {}) or {}
    judge = raw.get("llm_judge", {}) or {}

    judge_dims = [judge.get(k) for k in ("correctness", "completeness", "citation_quality", "clarity")]
    judge_dims = [d for d in judge_dims if d is not None]
    llm_judge_avg = sum(judge_dims) / len(judge_dims) if judge_dims else None

    citation_coverage = _citation_coverage(golden_set)
    leakage = _role_filter_leakage_rate(golden_set)
    role_approp = _role_appropriateness_avg(golden_set)
    reg_compliance = _regulatory_compliance_avg(golden_set)
    stability = _answer_stability_avg(golden_set)

    measured = {
        "hit_rate_at_5": intrinsic.get("hit_rate_at_5"),
        "mrr": intrinsic.get("mrr"),
        "faithfulness": extrinsic.get("faithfulness"),
        "answer_correctness": extrinsic.get("answer_correctness"),
        "llm_judge_avg": llm_judge_avg,
        "citation_coverage": citation_coverage["value"],
        "role_filter_leakage_rate": leakage["value"],
        "role_appropriateness": role_approp["value"],
        "regulatory_compliance_score": reg_compliance["value"],
        "answer_stability": stability["value"],
    }

    checks = {
        metric: {
            "value": value,
            "threshold": ACCEPTANCE_THRESHOLDS.get(metric),
            "passed": None if metric in UNGATED_METRICS else _passes(metric, value),
        }
        for metric, value in measured.items()
    }

    evaluated = [c["passed"] for c in checks.values() if c["passed"] is not None]
    overall_pass_rate = sum(evaluated) / len(evaluated) if evaluated else None

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "overall_pass_rate": overall_pass_rate,
        "overall_pass": all(evaluated) if evaluated else None,
        "n_items": raw.get("n_items"),
        "citation_coverage_n": citation_coverage["n"],
        "role_filter_leakage_n": leakage["n"],
        "role_appropriateness_n": role_approp["n"],
        "regulatory_compliance_n": reg_compliance["n"],
        "answer_stability_n": stability["n"],
    }

    os.makedirs("reports/regression_history", exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(f"reports/regression_history/{ts}.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open("reports/eval_week4_final.md", "w") as f:
        f.write(f"# Regression Suite Result ({report['timestamp']})\n\n```json\n{json.dumps(report, indent=2, default=str)}\n```\n")

    return report