# FILE: rag/vectorstores/base.py
from abc import ABC, abstractmethod


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[dict], embedder) -> None: ...

    @abstractmethod
    def search(self, query: str, embedder, k: int = 5, filters: dict = None) -> list[dict]: ...

    @abstractmethod
    def delete(self, doc_id: str) -> None: ...

    @abstractmethod
    def persist(self, path: str) -> None: ...

    @abstractmethod
    def load(self, path: str, embedder) -> None: ...