# FILE: rag/contextualizer.py
"""Rewrites a possibly-elliptical follow-up query into a standalone query,
using recent conversation history, before it hits retrieval.

This is the "condense question" step conversational RAG pipelines rely on.
Without it, a follow-up like "What about for loan against property?" (asked
right after a home-loan LTV question) gets embedded and BM25-searched as a
bare 6-word fragment with no referent -- so retrieval, reranking, and the
final cited answer all degrade even though those stages are individually
working correctly. This module is the fix for that specific gap.
"""
from services.llm_service import get_llm
from utils.logger import get_logger

logger = get_logger("rag.contextualizer")

CONTEXTUALIZE_PROMPT = """Given the conversation history and a follow-up question, rewrite the \
follow-up question into a standalone question that contains all the \
context needed to understand it WITHOUT the history. If the follow-up \
question is already standalone (no pronouns, no implicit reference to \
something discussed earlier), return it UNCHANGED.

Do not answer the question. Return ONLY the rewritten question -- no \
preamble, no quotes, no explanation.

Conversation history:
{history}

Follow-up question: {question}

Standalone question:"""


def _format_history_for_contextualizer(history: list, max_turns: int = 4) -> str:
    """`history` is a list of {"user": ..., "assistant": ...} dicts from
    MemoryStore.get(). Only the most recent `max_turns` are used -- older
    turns rarely help disambiguate a follow-up and only add noise/cost to
    the rewrite call."""
    if not history:
        return "(none)"
    recent = history[-max_turns:]
    lines = []
    for turn in recent:
        lines.append(f"User: {turn.get('user', '')}")
        lines.append(f"Assistant: {turn.get('assistant', '')}")
    return "\n".join(lines)


def contextualize_query(question: str, history: list) -> str:
    """Returns a standalone version of `question`. Falls back to the
    original question (never raises) if the rewrite call fails or history is
    empty -- RAG should degrade to today's single-turn behavior, not break,
    if this step fails."""
    if not history:
        return question

    try:
        llm = get_llm(temperature=0)
        history_text = _format_history_for_contextualizer(history)
        prompt = CONTEXTUALIZE_PROMPT.format(history=history_text, question=question)
        response = llm.invoke(prompt)
        rewritten = response.content.strip().strip('"')
        if rewritten:
            if rewritten.lower() != question.strip().lower():
                logger.info(
                    "Contextualized RAG query | original=%.80s | rewritten=%.80s",
                    question, rewritten,
                )
            return rewritten
    except Exception:
        logger.exception("Query contextualization failed; falling back to original question.")

    return question