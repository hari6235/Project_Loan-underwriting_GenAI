# FILE: rag/state.py
"""Single shared instance of embedder / vector store / BM25 index, so /ingest,
/chat, /retrieve, and /evaluate never operate on divergent copies."""
from rag.embeddings import get_embedder
from rag.vectorstores.faiss_store import FAISSStore
from rag.retriever_bm25 import BM25Retriever

embedder = get_embedder()

vector_store = FAISSStore()
vector_store.load(embedder=embedder)


def _build_bm25() -> BM25Retriever:
    chunks = list(vector_store.index.docstore._dict.values()) if vector_store.index else []
    return BM25Retriever([{"text": d.page_content, "metadata": d.metadata} for d in chunks])


bm25_retriever = _build_bm25()


def refresh_bm25() -> None:
    """Call after any add()/delete() on vector_store so sparse search stays in sync."""
    global bm25_retriever
    bm25_retriever = _build_bm25()