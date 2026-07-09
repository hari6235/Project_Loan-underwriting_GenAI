from services.llm_service import get_llm

CITATION_PROMPT = """You are a loan underwriting policy assistant. Answer the question using ONLY the context chunks below.
Every factual claim MUST be followed by a citation tag like [chunk_id: <id>].
If the answer is not in the context, say "I don't have this information in the indexed documents" - do not guess.
Context:
{context}
Question: {question}
Answer (with inline [chunk_id: ...] citations after every claim):"""

NOT_FOUND_MESSAGE = "I don't have this information in the indexed documents."


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[chunk_id: {c['metadata'].get('chunk_id')}] (source: {c['metadata'].get('source')}) {c['text']}"
        for c in chunks
    )


def answer_with_citations(question: str, retrieved_chunks: list[dict]) -> dict:
    if not retrieved_chunks:
        return {
            "answer": NOT_FOUND_MESSAGE,
            "citations": [],
        }

    llm = get_llm(temperature=0)  # grounded generation for RAG, independent of the app's default temperature
    context = build_context(retrieved_chunks)
    prompt = CITATION_PROMPT.format(context=context, question=question)
    response = llm.invoke(prompt)
    answer_text = response.content

    # Don't attach citations if the model itself says it couldn't answer,
    # or if it didn't actually cite any chunk_id in its answer.
    if NOT_FOUND_MESSAGE.lower() in answer_text.lower():
        return {"answer": answer_text, "citations": []}

    cited_ids = {
        c["metadata"].get("chunk_id")
        for c in retrieved_chunks
        if f"[chunk_id: {c['metadata'].get('chunk_id')}]" in answer_text
    }

    citations = [
        {
            "chunk_id": c["metadata"].get("chunk_id"),
            "doc_name": c["metadata"].get("source"),
            "page": c["metadata"].get("page"),
            "score": c.get("rerank_score", c.get("fused_score", c.get("score"))),
            "text": c["text"],
        }
        for c in retrieved_chunks
        if c["metadata"].get("chunk_id") in cited_ids
    ]

    return {"answer": answer_text, "citations": citations}