# FILE: rag/retriever_bm25.py
from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.corpus = [c["text"].split() for c in chunks]
        self.bm25 = BM25Okapi(self.corpus) if self.corpus else None

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(query.split())
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)[:k]
        return [{"text": c["text"], "metadata": c["metadata"], "score": float(s)} for c, s in ranked]