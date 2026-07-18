# FILE: callbacks/metrics.py
"""Custom callback handler that emits lightweight in-memory metrics
(latency, tool-call counts, error counts) for a chain run -- consumed by
eval/dashboard.py's trend visualisation and eval/custom_metrics.py."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler


class MetricsCallback(BaseCallbackHandler):
    def __init__(self):
        self.tool_call_count: int = 0
        self.tool_error_count: int = 0
        self.chain_error_count: int = 0
        self.latencies_ms: dict[str, list[float]] = defaultdict(list)
        self._starts: dict[UUID, float] = {}

    def on_chain_start(self, serialized: dict, inputs: dict, *, run_id: UUID, **kwargs: Any) -> None:
        self._starts[run_id] = time.monotonic()

    def on_chain_end(self, outputs: dict, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._starts.pop(run_id, None)
        if start is not None:
            self.latencies_ms["chain"].append((time.monotonic() - start) * 1000)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self.chain_error_count += 1
        self._starts.pop(run_id, None)

    def on_tool_start(self, serialized: dict, input_str: str, *, run_id: UUID, **kwargs: Any) -> None:
        self.tool_call_count += 1
        self._starts[run_id] = time.monotonic()

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._starts.pop(run_id, None)
        if start is not None:
            self.latencies_ms["tool"].append((time.monotonic() - start) * 1000)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self.tool_error_count += 1
        self._starts.pop(run_id, None)

    def snapshot(self) -> dict:
        def _avg(vals: list[float]) -> float | None:
            return round(sum(vals) / len(vals), 1) if vals else None

        return {
            "tool_call_count": self.tool_call_count,
            "tool_error_count": self.tool_error_count,
            "chain_error_count": self.chain_error_count,
            "avg_chain_latency_ms": _avg(self.latencies_ms["chain"]),
            "avg_tool_latency_ms": _avg(self.latencies_ms["tool"]),
        }