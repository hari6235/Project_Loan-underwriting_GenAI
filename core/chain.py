# FILE: core/chain.py
"""Thin compatibility wrapper: api/routes.py calls run_chain(), which now
delegates to the LCEL chain registry (chains/router.py) instead of the old
hardcoded keyword cascade (tools/router.py, deleted) or a raw LLM-only
fallback. All routing -- tool selection, RAG, HITL gating -- happens
inside the chain registry; this function's only remaining job is to keep
api/routes.py's call signature stable.
"""
from chains.router import route


def run_chain(user_input: str, history: list, session_id: str = "", role: str = "junior_analyst") -> dict:
    return route(user_input, history, session_id=session_id, role=role)