# FILE: callbacks/logging.py
"""Custom LangChain callback handler for structured logging of chain/tool
execution (Section 3.2: "custom callback handlers for structured logging,
LangSmith tracing, and metric emission")."""
from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler

from utils.logger import get_logger

logger = get_logger("callbacks.logging")


class StructuredLoggingCallback(BaseCallbackHandler):
    def __init__(self):
        self._starts: dict[UUID, float] = {}

    def on_chain_start(self, serialized: dict, inputs: dict, *, run_id: UUID, **kwargs: Any) -> None:
        self._starts[run_id] = time.monotonic()
        name = (serialized or {}).get("name", "chain")
        logger.info("chain_start name=%s run_id=%s", name, run_id)

    def on_chain_end(self, outputs: dict, *, run_id: UUID, **kwargs: Any) -> None:
        elapsed = self._elapsed(run_id)
        logger.info("chain_end run_id=%s elapsed_ms=%.1f", run_id, elapsed)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        elapsed = self._elapsed(run_id)
        logger.error("chain_error run_id=%s elapsed_ms=%.1f error=%s", run_id, elapsed, error)

    def on_tool_start(self, serialized: dict, input_str: str, *, run_id: UUID, **kwargs: Any) -> None:
        self._starts[run_id] = time.monotonic()
        name = (serialized or {}).get("name", "tool")
        logger.info("tool_start name=%s run_id=%s input_preview=%.100s", name, run_id, input_str)

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        elapsed = self._elapsed(run_id)
        logger.info("tool_end run_id=%s elapsed_ms=%.1f", run_id, elapsed)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        elapsed = self._elapsed(run_id)
        logger.error("tool_error run_id=%s elapsed_ms=%.1f error=%s", run_id, elapsed, error)

    def _elapsed(self, run_id: UUID) -> float:
        start = self._starts.pop(run_id, None)
        return (time.monotonic() - start) * 1000 if start is not None else -1.0