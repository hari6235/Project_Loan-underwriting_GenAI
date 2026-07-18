# FILE: rag/retriever_hybrid.py
"""Fuses dense (vector store) + sparse (BM25) results via Reciprocal Rank Fusion."""


def reciprocal_rank_fusion(dense_results: list[dict], sparse_results: list[dict], k: int = 60) -> list[dict]:
    scores = {}
    store = {}

    for rank, r in enumerate(dense_results):
        cid = r["metadata"].get("chunk_id", r["text"][:50])
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        store[cid] = r

    for rank, r in enumerate(sparse_results):
        cid = r["metadata"].get("chunk_id", r["text"][:50])
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        store[cid] = r

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{**store[cid], "fused_score": s} for cid, s in fused]


def hybrid_search(query: str, vector_store, bm25_retriever, embedder, k: int = 10, filters: dict = None) -> list[dict]:
    dense = vector_store.search(query, embedder, k=k, filters=filters)
    sparse = bm25_retriever.search(query, k=k, filters=filters)
    return reciprocal_rank_fusion(dense, sparse)[:k]