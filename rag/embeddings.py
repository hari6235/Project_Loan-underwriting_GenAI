# FILE: rag/embeddings.py
"""Embedding adapter - swap provider via env var EMBEDDING_PROVIDER."""
import os


def get_embedder():
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small")
    elif provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    elif provider == "cohere":
        from langchain_cohere import CohereEmbeddings
        return CohereEmbeddings(model="embed-english-v3.0")
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")