from rag.state import embedder, vector_store, bm25_retriever
from rag.retriever_hybrid import hybrid_search
from rag.reranker import rerank
from rag.qa_chain import answer_with_citations
from rag.contextualizer import contextualize_query


def knowledge_retrieval(query: str, filters: dict = None, k: int = 5, history: list = None) -> dict:
    """Agent-callable RAG tool: retrieve + rerank + answer with citations.
    Returns {"type": "rag_response", "response": ..., "citations": [...]}."""
    resolved_query = contextualize_query(query, history) if history else query

    candidates = hybrid_search(resolved_query, vector_store, bm25_retriever, embedder, k=10, filters=filters)
    top = rerank(resolved_query, candidates, top_k=k)
    result = answer_with_citations(resolved_query, top)
    return {
        "type": "rag_response",
        "response": result["answer"],
        "citations": result["citations"],
    }