# FILE: eval/run_eval.py
"""Core evaluation entry point (Week 6 baseline, extended in Week 8 with
role-awareness). retrieve_fn/answer_fn now take the full golden-set item
so item["role"] can drive RBAC-aware retrieval -- required for the
role_boundary_test category to test anything meaningful."""
import json
import os

from eval.intrinsic import run_intrinsic
from eval.extrinsic import run_extrinsic
from eval.llm_judge import run_llm_judge
from rag.state import embedder, vector_store, bm25_retriever
from rag.retriever_hybrid import hybrid_search
from rag.reranker import rerank
from rag.contextualizer import contextualize_query
from rbac.filter import build_role_filter, merge_filters
from rbac.validator import validate_no_leakage
from rbac.role_registry import get_role_registry
from tools.rag_tool import knowledge_retrieval


def retrieve_fn(item: dict) -> list[dict]:
    """Mirrors tools/rag_tool.py's retrieval path exactly (contextualize ->
    role-filtered hybrid search -> rerank -> post-retrieval validation) so
    intrinsic metrics measure what /chat actually returns."""
    role = item.get("role", "junior_analyst")
    history = item.get("history", [])
    registry = get_role_registry()

    standalone_query = contextualize_query(item["query"], history)
    role_filter = build_role_filter(role, registry)
    merged = merge_filters(role_filter, None)

    candidates = hybrid_search(standalone_query, vector_store, bm25_retriever, embedder, k=10, filters=merged)
    reranked = rerank(standalone_query, candidates, top_k=5)
    return validate_no_leakage(role, reranked, registry, raise_on_leak=False)


def answer_fn(item: dict) -> dict:
    role = item.get("role", "junior_analyst")
    history = item.get("history", [])
    return knowledge_retrieval(item["query"], history=history, role=role)


def load_golden_set(bucket: str | None = None, category: str | None = None) -> list[dict]:
    with open("eval/golden_set.json") as f:
        golden_set = json.load(f)
    if bucket:
        golden_set = [g for g in golden_set if g.get("eval_bucket") == bucket]
    if category:
        golden_set = [g for g in golden_set if g.get("category") == category]
    return golden_set


def run_full_eval() -> dict:
    golden_set = load_golden_set()
    retrieval_items = [g for g in golden_set if g.get("eval_bucket") in ("rag", "hybrid")]

    results = {
        "n_items": {
            "total": len(golden_set),
            "rag": sum(1 for g in golden_set if g.get("eval_bucket") == "rag"),
            "tool": sum(1 for g in golden_set if g.get("eval_bucket") == "tool"),
            "hybrid": sum(1 for g in golden_set if g.get("eval_bucket") == "hybrid"),
        },
        "intrinsic": run_intrinsic(retrieval_items, retrieve_fn),
        "extrinsic": run_extrinsic(retrieval_items, answer_fn),
        "llm_judge": run_llm_judge(retrieval_items, answer_fn),
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/eval_baseline.md", "w") as f:
        f.write(f"# Eval Results\n\n```json\n{json.dumps(results, indent=2)}\n```\n")

    return results