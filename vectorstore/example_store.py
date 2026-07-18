# FILE: vectorstore/example_store.py
"""Lazy-built few-shot example lookup. Deliberately does NOT build the
FAISS index at import time (the old version did, which meant importing
this module at all -- even transitively -- required a live OPENAI_API_KEY
and made a network call just to load Python code). The index is now built
once on first use and cached."""
import os

import yaml

_EXAMPLES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "few_shots.yaml")

_vectorstore = None


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings

    with open(_EXAMPLES_PATH, "r") as f:
        data = yaml.safe_load(f)

    examples = [{"question": ex["user"], "answer": str(ex["assistant"])} for ex in data["examples"]]
    texts = [e["question"] for e in examples]
    metadatas = [{"answer": e["answer"]} for e in examples]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set -- required to build the few-shot example index.")

    _vectorstore = FAISS.from_texts(texts=texts, embedding=OpenAIEmbeddings(api_key=api_key), metadatas=metadatas)
    return _vectorstore


def search_examples(query: str):
    """Returns the closest matching few-shot answer, or None if the index
    can't be built (e.g. no API key) -- callers must treat this as
    optional enrichment, never a hard dependency."""
    try:
        vectorstore = _get_vectorstore()
    except Exception:
        return None
    docs = vectorstore.similarity_search(query, k=1)
    return docs[0].metadata["answer"] if docs else None