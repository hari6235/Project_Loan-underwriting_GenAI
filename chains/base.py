# FILE: chains/base.py
"""Shared LCEL building blocks: RunnableConfig metadata propagation (user
role, session ID, trace ID), retry/fallback wrapping, and the tool
catalogue (local + MCP) every chain binds against.

Every chain in this package is a Runnable composed with the `|` operator
per Section 3.2's "Key patterns to implement" -- this file provides the
pieces the others compose.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from services.llm_service import get_llm
from tools.tool_registry import TOOLS as LOCAL_TOOLS
from utils.logger import get_logger

logger = get_logger("chains.base")


def build_request_config(session_id: str, role: str, trace_id: str | None = None) -> RunnableConfig:
    """Request-scoped metadata threaded through every Runnable in a chain
    via RunnableConfig, so callbacks (callbacks/logging.py,
    callbacks/metrics.py) and any node in the chain can read the current
    user's role/session without it being passed as an explicit argument
    everywhere."""
    return RunnableConfig(
        metadata={"session_id": session_id, "role": role, "trace_id": trace_id or session_id},
        tags=[f"role:{role}"],
        run_name="loan_underwriting_turn",
    )


def all_tools() -> list:
    """Local deterministic/RAG tools + MCP-backed tools, presented to the
    agent as one uniform catalogue (Section 3.1: 'the agent treats MCP
    tools identically to local tools'). MCP tools are imported lazily so a
    missing/broken MCP config doesn't break every chain that imports this
    module -- it degrades to local-tools-only with a logged warning."""
    tools = list(LOCAL_TOOLS)
    try:
        from mcp.tool_adapter import build_mcp_tools
        tools.extend(build_mcp_tools())
    except Exception:
        logger.exception("Failed to build MCP tools -- continuing with local tools only.")
    return tools


def llm_with_retry_and_fallback(temperature: float | None = None):
    """LCEL retry/fallback pattern (Section 3.2): the primary model gets 2
    retries with exponential backoff via .with_retry(); if it's still
    failing, falls back to a lower-temperature call on the same model
    family as a degraded-but-available path, per the 'fallback chains for
    graceful degradation' requirement."""
    primary = get_llm(temperature=temperature)
    fallback = get_llm(temperature=0.0)
    return primary.with_retry(stop_after_attempt=3).with_fallbacks([fallback])