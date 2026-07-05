# FILE: rag/vectorstores/faiss_store.py
import os
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from rag.vectorstores.base import VectorStore

DEFAULT_INDEX_DIR = "data/vector_index/faiss"


class FAISSStore(VectorStore):
    def __init__(self):
        self.index = None

    def add(self, chunks: list[dict], embedder) -> None:
        docs = [Document(page_content=c["text"], metadata=c["metadata"]) for c in chunks]
        if self.index is None:
            self.index = FAISS.from_documents(docs, embedder)
        else:
            self.index.add_documents(docs)

    def search(self, query: str, embedder, k: int = 5, filters: dict = None) -> list[dict]:
        if self.index is None:
            return []
        results = self.index.similarity_search_with_score(query, k=k)
        out = []
        for doc, score in results:
            if filters and not all(doc.metadata.get(fk) == fv for fk, fv in filters.items()):
                continue
            out.append({"text": doc.page_content, "metadata": doc.metadata, "score": float(score)})
        return out

    def delete(self, doc_id: str) -> None:
        # FAISS's langchain wrapper has no native delete-by-metadata, so we
        # rebuild the index excluding chunks whose "source" matches doc_id.
        if self.index is None:
            return
        remaining = [
            (d.page_content, d.metadata)
            for d in self.index.docstore._dict.values()
            if d.metadata.get("source") != doc_id
        ]
        if remaining:
            texts, metas = zip(*remaining)
            self.index = FAISS.from_texts(list(texts), self.index.embedding_function, metadatas=list(metas))
        else:
            self.index = None

    def persist(self, path: str = DEFAULT_INDEX_DIR) -> None:
        os.makedirs(path, exist_ok=True)
        if self.index:
            self.index.save_local(path)

    def load(self, path: str = DEFAULT_INDEX_DIR, embedder=None) -> None:
        if os.path.exists(path):
            self.index = FAISS.load_local(path, embedder, allow_dangerous_deserialization=True)