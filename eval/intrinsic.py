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
    hits, mrrs = [], []
    for item in golden_set:
        retrieved = retrieve_fn(item["query"], item.get("history", []))
        ids = [r["metadata"].get("chunk_id") for r in retrieved]
        hits.append(hit_at_k(ids, item["expected_chunk_ids"]))
        mrrs.append(mrr(ids, item["expected_chunk_ids"]))
    return {"hit_rate_at_5": sum(hits) / len(hits), "mrr": sum(mrrs) / len(mrrs)}