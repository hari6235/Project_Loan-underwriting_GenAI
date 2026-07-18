# FILE: chains/router.py
"""Chain registry (Section 3.2): maps intent categories to specific
chains, and wires a fallback chain for graceful degradation via
.with_fallbacks() -- if the full agent+HITL chain raises, the turn still
gets a usable (degraded) answer instead of a raw 500.

This is the single entry point core/chain.py's run_chain() calls.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig, RunnableLambda

from chains.base import build_request_config
from chains.hitl_chain import hitl_chain
from services.llm_service import get_llm
from utils.logger import get_logger

logger = get_logger("chains.router")

_GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}


def _classify_intent(user_input: str) -> str:
    """Coarse intent classification: 'greeting' skips the full tool-bound
    agent (no tools needed for "hi"); everything else goes through the
    full agent+HITL chain. This keeps the chain registry genuinely
    intent-driven rather than a single hardcoded path, per the deliverable."""
    normalized = user_input.strip().lower().rstrip("!.")
    if normalized in _GREETINGS:
        return "greeting"
    return "full_agent"


def _greeting_chain_run(payload: dict, config: RunnableConfig | None = None) -> dict:
    return {
        "type": "llm_response",
        "response": (
            "Hello! I'm your Loan Underwriting & Credit Risk Assistant. "
            "I can help with credit score analysis, DTI calculations, KYC verification, "
            "policy/regulatory lookups, and underwriting recommendations. How can I help?"
        ),
    }


def _fallback_chain_run(payload: dict, config: RunnableConfig | None = None) -> dict:
    """Degraded path used only when the full agent+HITL chain raises.
    No tools, no RAG -- a direct, conservative LLM response that still
    tells the user something useful went wrong rather than a bare error."""
    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke(
            "You are a banking assistant currently running in a degraded fallback mode "
            "(tools are temporarily unavailable). Politely tell the user their request "
            "couldn't be fully processed right now and ask them to retry shortly. "
            f"Their message was: {payload.get('input', '')}"
        )
        return {"type": "degraded_response", "response": response.content}
    except Exception:
        logger.exception("Fallback chain also failed.")
        return {
            "type": "error",
            "response": "The assistant is temporarily unavailable. Please try again shortly.",
        }


greeting_chain = RunnableLambda(_greeting_chain_run).with_config({"run_name": "greeting_chain"})
fallback_chain = RunnableLambda(_fallback_chain_run).with_config({"run_name": "fallback_chain"})

# Graceful degradation: if the full agent+HITL chain throws for any reason
# (LLM outage, tool crash not otherwise caught, etc.), fall back rather
# than propagate a 500 to the user.
full_agent_chain_with_fallback = hitl_chain.with_fallbacks([fallback_chain])

CHAIN_REGISTRY = {
    "greeting": greeting_chain,
    "full_agent": full_agent_chain_with_fallback,
}


def route(user_input: str, history: list, session_id: str, role: str) -> dict:
    intent = _classify_intent(user_input)
    chain = CHAIN_REGISTRY[intent]
    config = build_request_config(session_id=session_id, role=role)

    payload = {"input": user_input, "history": history, "session_id": session_id, "role": role}
    logger.info("Routed intent=%s session=%s role=%s", intent, session_id, role)
    return chain.invoke(payload, config=config)