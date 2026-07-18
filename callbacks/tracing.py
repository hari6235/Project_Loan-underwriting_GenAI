# FILE: callbacks/tracing.py
"""Thin wrapper around LangSmith tracing so chains opt in consistently
instead of each module configuring it ad hoc. Delegates to the existing
utils/langsmith_config.py (already used by services/llm_service.py) rather
than duplicating env-var handling."""
from __future__ import annotations

from utils.langsmith_config import configure_langsmith
from utils.logger import get_logger

logger = get_logger("callbacks.tracing")

_configured = False


def ensure_tracing_configured() -> None:
    global _configured
    if _configured:
        return
    configure_langsmith()
    _configured = True
    logger.info("LangSmith tracing configured for chain execution.")