# FILE: tools/rag_tool.py
"""RAG tool with role-based access control (Section 3.6, Week 8): every
call filters retrieval to the requester's permitted doc_types BEFORE
hybrid search runs (rbac/filter.py), then validates the reranked result
set a second time AFTER reranking (rbac/validator.py) as defense in depth,
and writes an audit record of what was returned (rbac/audit.py).
"""
from rag.state import embedder, vector_store, bm25_retriever
from rag.retriever_hybrid import hybrid_search
from rag.reranker import rerank
from rag.qa_chain import answer_with_citations
from rag.contextualizer import contextualize_query
from rbac.filter import build_role_filter, merge_filters
from rbac.validator import validate_no_leakage
from rbac.audit import log_retrieval
from rbac.role_registry import get_role_registry
from utils.logger import get_logger

logger = get_logger("tools.rag_tool")


def knowledge_retrieval(
    query: str,
    filters: dict = None,
    k: int = 5,
    history: list = None,
    role: str = "junior_analyst",
    session_id: str = "",
) -> dict:
    """Role-aware, agent-callable RAG tool: contextualize -> role-filtered
    hybrid retrieve -> rerank -> post-retrieval leakage validation ->
    answer with citations -> audit log.

    Returns {"type": "rag_response", "response": ..., "citations": [...]}.
    """
    resolved_query = contextualize_query(query, history) if history else query

    registry = get_role_registry()
    role_filter = build_role_filter(role, registry)
    merged_filters = merge_filters(role_filter, filters)

    candidates = hybrid_search(resolved_query, vector_store, bm25_retriever, embedder, k=10, filters=merged_filters)
    reranked = rerank(resolved_query, candidates, top_k=k)

    # Post-retrieval validator: sanitize (drop + log) rather than hard-fail
    # the user's turn over what should be an internal bug -- but the leak
    # itself must never reach the answer, and it's logged loudly either way.
    pre_validation_ids = [c["metadata"].get("chunk_id") for c in reranked]
    clean = validate_no_leakage(role, reranked, registry, raise_on_leak=False)
    leaked_ids = [cid for cid in pre_validation_ids if cid not in {c["metadata"].get("chunk_id") for c in clean}]
    if leaked_ids:
        logger.error(
            "RBAC leakage caught post-retrieval for role=%s query=%.60s leaked_chunk_ids=%s",
            role, resolved_query, leaked_ids,
        )

    result = answer_with_citations(resolved_query, clean)

    log_retrieval(
        role_name=role,
        session_id=session_id,
        query=resolved_query,
        allowed_doc_types=role_filter["doc_type"]["$in"],
        returned_chunk_ids=[c["metadata"].get("chunk_id") for c in clean],
        leaked_and_dropped_chunk_ids=leaked_ids,
    )

    return {
        "type": "rag_response",
        "response": result["answer"],
        "citations": result["citations"],
    }