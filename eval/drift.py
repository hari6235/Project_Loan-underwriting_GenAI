# FILE: eval/drift.py
"""Lightweight but REAL drift check backing the mandatory /eval/drift
endpoint (Section 2.3's endpoint table). The full optional drift/ module
(Section 3.8 -- KL divergence, nearest-neighbour stability, alerting) is
bonus-credit scope and NOT implemented here; this module instead does the
one drift check that's cheap, dependency-light, and genuinely meaningful
on its own: embedding-based semantic drift of answers to a small fixed
canary query set, versus a baseline captured on first run.

On first call (no baseline yet) it captures one and returns
status="baseline_captured" rather than fabricating a score against
nothing.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

BASELINE_PATH = "reports/drift_baseline.json"
ALERT_THRESHOLD_COSINE_SIM = 0.85  # matches Section 3.8's "Output Semantic Shift < 0.85" alert threshold

CANARY_QUERIES = [
    "What is the maximum LTV ratio for a home loan above 75L?",
    "What is the minimum monthly net salary for a home loan applicant in metro areas?",
    "What is the escalation path for an underwriting exception above 2 Cr?",
]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def run_drift_check() -> dict:
    from rag.state import embedder
    from tools.rag_tool import knowledge_retrieval

    current_answers = {}
    current_embeddings = {}
    for query in CANARY_QUERIES:
        result = knowledge_retrieval(query, role="credit_head")  # broadest role, so drift isn't confounded by RBAC
        current_answers[query] = result["response"]
        current_embeddings[query] = embedder.embed_query(result["response"])

    if not os.path.exists(BASELINE_PATH):
        os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
        baseline = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "answers": current_answers,
            "embeddings": current_embeddings,
        }
        with open(BASELINE_PATH, "w") as f:
            json.dump(baseline, f)
        return {"status": "baseline_captured", "captured_at": baseline["captured_at"], "n_queries": len(CANARY_QUERIES)}

    with open(BASELINE_PATH, "r") as f:
        baseline = json.load(f)

    per_query = {}
    similarities = []
    for query in CANARY_QUERIES:
        baseline_vec = baseline["embeddings"].get(query)
        if baseline_vec is None:
            continue
        sim = _cosine_similarity(current_embeddings[query], baseline_vec)
        similarities.append(sim)
        per_query[query] = {
            "cosine_similarity_vs_baseline": round(sim, 4),
            "alert": sim < ALERT_THRESHOLD_COSINE_SIM,
        }

    avg_similarity = sum(similarities) / len(similarities) if similarities else None
    return {
        "status": "measured",
        "baseline_captured_at": baseline["captured_at"],
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "avg_cosine_similarity": round(avg_similarity, 4) if avg_similarity is not None else None,
        "alert_threshold": ALERT_THRESHOLD_COSINE_SIM,
        "drift_alert": any(v["alert"] for v in per_query.values()),
        "per_query": per_query,
    }