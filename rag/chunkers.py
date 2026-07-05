# FILE: rag/chunkers.py
"""Two chunking strategies: recursive and semantic."""
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_recursive(docs: list[dict], chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks = []
    for doc in docs:
        for i, piece in enumerate(splitter.split_text(doc["text"])):
            chunks.append({
                "text": piece,
                "metadata": {**doc["metadata"], "chunk_id": f"{doc['metadata'].get('source', 'doc')}_{i}"}
            })
    return chunks


def chunk_semantic(docs: list[dict], embedder, similarity_threshold: float = 0.75) -> list[dict]:
    """Groups consecutive sentences until embedding similarity drops below threshold."""
    import re
    import numpy as np

    chunks = []
    for doc in docs:
        sentences = re.split(r'(?<=[.!?])\s+', doc["text"])
        sentences = [s for s in sentences if s.strip()]
        if not sentences:
            continue
        embeddings = embedder.embed_documents(sentences)
        current = [sentences[0]]
        idx = 0
        for i in range(1, len(sentences)):
            sim = np.dot(embeddings[i - 1], embeddings[i]) / (
                np.linalg.norm(embeddings[i - 1]) * np.linalg.norm(embeddings[i]) + 1e-8
            )
            if sim < similarity_threshold:
                chunks.append({
                    "text": " ".join(current),
                    "metadata": {**doc["metadata"], "chunk_id": f"{doc['metadata'].get('source', 'doc')}_{idx}"}
                })
                idx += 1
                current = [sentences[i]]
            else:
                current.append(sentences[i])
        if current:
            chunks.append({
                "text": " ".join(current),
                "metadata": {**doc["metadata"], "chunk_id": f"{doc['metadata'].get('source', 'doc')}_{idx}"}
            })
    return chunks


def chunk_documents(docs: list[dict], strategy: str = "recursive", embedder=None) -> list[dict]:
    if strategy == "semantic":
        if embedder is None:
            raise ValueError("semantic chunking requires an embedder instance")
        return chunk_semantic(docs, embedder)
    return chunk_recursive(docs)