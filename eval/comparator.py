# FILE: eval/comparator.py
"""Version A vs Version B comparison mode (Section 3.5) -- e.g. comparing
eval results before/after a prompt rollback or model swap. Pure stdlib,
operates on the same report dict shape eval/regression_suite.py produces
(or any two dicts loaded from reports/regression_history/*.json)."""
from __future__ import annotations


def compare_reports(report_a: dict, report_b: dict, label_a: str = "A", label_b: str = "B") -> dict:
    """Returns a per-metric delta table plus a plain-language verdict.
    Metrics only present in one report are reported with the other side
    as None rather than silently skipped."""
    checks_a = report_a.get("checks", {})
    checks_b = report_b.get("checks", {})
    all_metrics = sorted(set(checks_a) | set(checks_b))

    deltas = {}
    regressions = []
    improvements = []
    for metric in all_metrics:
        val_a = checks_a.get(metric, {}).get("value")
        val_b = checks_b.get(metric, {}).get("value")
        delta = (val_b - val_a) if (val_a is not None and val_b is not None) else None
        deltas[metric] = {label_a: val_a, label_b: val_b, "delta": delta}

        if delta is None:
            continue
        # role_filter_leakage_rate is the one metric where LOWER is better.
        improved = (delta < 0) if metric == "role_filter_leakage_rate" else (delta > 0)
        if improved and abs(delta) > 1e-9:
            improvements.append(metric)
        elif not improved and abs(delta) > 1e-9:
            regressions.append(metric)

    return {
        "label_a": label_a,
        "label_b": label_b,
        "deltas": deltas,
        "improvements": improvements,
        "regressions": regressions,
        "verdict": "regression_detected" if regressions else ("improved" if improvements else "no_change"),
    }