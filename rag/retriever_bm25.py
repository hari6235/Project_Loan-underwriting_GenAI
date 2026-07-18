# FILE: rag/retriever_bm25.py
from rank_bm25 import BM25Okapi

from rag.filters import matches_filters


class BM25Retriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.corpus = [c["text"].split() for c in chunks]
        self.bm25 = BM25Okapi(self.corpus) if self.corpus else None

    def search(self, query: str, k: int = 5, filters: dict = None) -> list[dict]:
        """filters is applied BEFORE truncating to top-k, using the same
        matches_filters() DSL as the dense (FAISS) leg -- this is what
        keeps sparse retrieval from being an unfiltered leakage path for
        role-based (or any other) metadata restrictions."""
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(query.split())
        scored = list(zip(self.chunks, scores))
        if filters:
            scored = [(c, s) for c, s in scored if matches_filters(c["metadata"], filters)]
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)[:k]
        return [{"text": c["text"], "metadata": c["metadata"], "score": float(s)} for c, s in ranked]