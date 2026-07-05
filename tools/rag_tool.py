# FILE: tools/rag_tool.py
from rag.state import embedder, vector_store, bm25_retriever
from rag.retriever_hybrid import hybrid_search
from rag.reranker import rerank
from rag.qa_chain import answer_with_citations


def knowledge_retrieval(query: str, filters: dict = None, k: int = 5) -> dict:
    """Agent-callable RAG tool: retrieve + rerank + answer with citations.
    Returns {"type": "rag_response", "response": ..., "citations": [...]}."""
    candidates = hybrid_search(query, vector_store, bm25_retriever, embedder, k=10, filters=filters)
    top = rerank(query, candidates, top_k=k)
    result = answer_with_citations(query, top)
    return {
        "type": "rag_response",
        "response": result["answer"],
        "citations": result["citations"],
    }