# FILE: chains/rag_chain.py
"""Standalone LCEL RAG chain, usable independently of the tool-calling
agent (e.g. by /retrieve-adjacent debugging paths or eval/regression_suite.py
that want a direct RAG answer without going through tool-routing).

Composed with RunnableParallel (fetch role-filtered context + pass the
question through unchanged) followed by the versioned rag_qa_chain prompt
(prompts/rag_qa.yaml) piped into the LLM -- the literal LCEL pattern from
Section 3.2 ("RunnablePassthrough | RunnableLambda | RunnableParallel for
composable pipelines").
"""
from __future__ import annotations

from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough

from prompt_manager.registry import get_prompt_registry
from rag.state import embedder, vector_store, bm25_retriever
from rag.retriever_hybrid import hybrid_search
from rag.reranker import rerank
from rbac.filter import build_role_filter, merge_filters
from rbac.validator import validate_no_leakage
from rbac.audit import log_retrieval
from rbac.role_registry import get_role_registry
from services.llm_service import get_llm


def _format_context(chunks: list[dict]) -> str:
    lines = []
    for c in chunks:
        cid = c["metadata"].get("chunk_id", "unknown")
        lines.append(f"[chunk_id: {cid}] {c['text']}")
    return "\n\n".join(lines) if lines else "(no matching context found)"


def _retrieve_role_filtered(payload: dict) -> dict:
    """payload: {"question": str, "role": str, "session_id": str}."""
    role = payload.get("role", "junior_analyst")
    session_id = payload.get("session_id", "")
    registry = get_role_registry()

    role_filter = build_role_filter(role, registry)
    merged = merge_filters(role_filter, None)

    candidates = hybrid_search(payload["question"], vector_store, bm25_retriever, embedder, k=10, filters=merged)
    reranked = rerank(payload["question"], candidates, top_k=5)
    clean = validate_no_leakage(role, reranked, registry, raise_on_leak=False)

    log_retrieval(
        role_name=role,
        session_id=session_id,
        query=payload["question"],
        allowed_doc_types=role_filter["doc_type"]["$in"],
        returned_chunk_ids=[c["metadata"].get("chunk_id") for c in clean],
    )
    return {"chunks": clean, "context": _format_context(clean)}


def _build_prompt(payload: dict) -> str:
    prompt_version = get_prompt_registry().get_active("rag_qa_chain")
    render_kwargs = {"context": payload["context"], "question": payload["question"]}
    if "role" in prompt_version.input_variables:
        render_kwargs["role"] = payload.get("role", "junior_analyst")
    return prompt_version.render(**render_kwargs)


def _to_answer(payload: dict) -> dict:
    llm = get_llm(temperature=0.0)
    prompt_text = _build_prompt(payload)
    response = llm.invoke(prompt_text)
    citations = [
        {
            "chunk_id": c["metadata"].get("chunk_id"),
            "doc_name": c["metadata"].get("source"),
            "page": c["metadata"].get("page"),
            "score": c.get("score"),
            "text": c["text"],
        }
        for c in payload["retrieval"]["chunks"]
    ]
    return {"type": "rag_response", "response": response.content, "citations": citations}


# RunnableParallel: fan out to retrieval while the question/role/session_id
# pass through unchanged (RunnablePassthrough), then compose into the answer.
rag_chain = (
    RunnableParallel(
        retrieval=RunnableLambda(_retrieve_role_filtered),
        question=RunnableLambda(lambda p: p["question"]),
        role=RunnableLambda(lambda p: p.get("role", "junior_analyst")),
    )
    | RunnableLambda(lambda p: {**p, "context": p["retrieval"]["context"]})
    | RunnableLambda(_to_answer)
).with_config({"run_name": "rag_chain"})