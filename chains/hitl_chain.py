# FILE: chains/hitl_chain.py
"""HITL gate: wraps chains/tool_chain.py's output and checks the
accumulated decision_context (tool outputs from this turn) against
config/hitl_rules.yaml. If a rule fires, execution pauses -- the turn
returns type="pending_approval" with a task_id instead of the normal
answer, and the caller must poll GET /hitl/pending or wait for
POST /hitl/review/{task_id} to resume (Section 3.3).
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig, RunnableLambda

from chains.tool_chain import tool_chain
from hitl.manager import HITLManager, get_manager
from utils.logger import get_logger

logger = get_logger("chains.hitl_chain")


def _make_run(manager: HITLManager):
    def _run(payload: dict, config: RunnableConfig | None = None) -> dict:
        session_id = payload.get("session_id", "")
        agent_result = tool_chain.invoke(payload, config=config)

        decision_context = agent_result.get("decision_context") or {}
        if payload.get("policy_override_requested"):
            decision_context["policy_override_requested"] = True

        if not decision_context:
            return agent_result

        task = manager.check_and_create(
            session_id=session_id,
            decision_context=decision_context,
            recommendation=str(agent_result.get("response", "")),
            confidence_score=payload.get("confidence_score"),
        )
        if task is None:
            return agent_result

        logger.info("HITL gate paused turn for session=%s task_id=%s", session_id, task.task_id)
        return {
            "type": "pending_approval",
            "response": (
                "This recommendation requires human approval before it can be finalised "
                f"(triggered: {', '.join(task.triggered_rule_ids)}). "
                "It has been queued for review."
            ),
            "hitl_task_id": task.task_id,
            "hitl_severity": task.severity,
            "underlying_recommendation": agent_result.get("response"),
            "citations": agent_result.get("citations", []),
        }

    return _run


def build_hitl_chain(manager: HITLManager | None = None):
    return RunnableLambda(_make_run(manager or get_manager())).with_config({"run_name": "hitl_chain"})


hitl_chain = build_hitl_chain()