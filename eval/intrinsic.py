# FILE: eval/intrinsic.py
def hit_at_k(retrieved_ids: list[str], expected_ids: list[str]) -> int:
    if not expected_ids:
        return 1  # refusal cases: "hit" means nothing was wrongly retrieved as confident fact
    return int(any(rid in expected_ids for rid in retrieved_ids))


def mrr(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in expected_ids:
            return 1.0 / rank
    return 0.0


def run_intrinsic(golden_set: list[dict], retrieve_fn) -> dict:
    """retrieve_fn(item: dict) -> list[dict] of reranked chunks. Takes the
    full golden-set item (not just query/history) so retrieve_fn can honor
    item["role"] for RBAC-aware retrieval -- otherwise a role_boundary_test
    item would be retrieved under the wrong (or no) role and the metric
    would silently measure the wrong thing."""
    hits, mrrs = [], []
    for item in golden_set:
        retrieved = retrieve_fn(item)
        ids = [r["metadata"].get("chunk_id") for r in retrieved]
        hits.append(hit_at_k(ids, item["expected_chunk_ids"]))
        mrrs.append(mrr(ids, item["expected_chunk_ids"]))
    return {"hit_rate_at_5": sum(hits) / len(hits) if hits else None, "mrr": sum(mrrs) / len(mrrs) if mrrs else None, "n": len(golden_set)}