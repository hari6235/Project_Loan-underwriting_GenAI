# FILE: chains/tool_chain.py
"""The core agent loop, composed as an LCEL Runnable. The LLM is bound to
every tool -- local deterministic, RAG (knowledge_retrieval, itself
RBAC-aware), and MCP-backed -- and decides per turn which to call,
including calling several in one turn. This supersedes the old
tools/router.py keyword cascade entirely.

The system prompt is sourced from prompt_manager (prompts/agent_system.yaml)
-- never hardcoded here -- so prompt changes are versioned, diffable, and
rollbackable per Section 3.4.
"""
from __future__ import annotations

import json

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda

from chains.base import all_tools
from prompt_manager.registry import get_prompt_registry
from services.llm_service import get_llm
from utils.logger import get_logger

logger = get_logger("chains.tool_chain")

MAX_TOOL_ITERATIONS = 5


def _build_doc_type_filters(args: dict) -> dict | None:
    """Extracts any caller(LLM)-supplied doc_type/jurisdiction hints from
    the tool-call args. These are advisory only -- rbac/filter.py's role
    filter always overrides doc_type inside tools/rag_tool.py, so this
    can never be used to widen access."""
    filters = {}
    if args.get("doc_type"):
        filters["doc_type"] = args["doc_type"]
    if args.get("jurisdiction"):
        filters["jurisdiction"] = args["jurisdiction"]
    return filters or None


def _history_to_messages(history: list) -> list:
    messages = []
    for turn in history or []:
        user_msg = turn.get("user", "")
        assistant_raw = turn.get("assistant", "")
        try:
            parsed = json.loads(assistant_raw)
            assistant_msg = parsed.get("response", assistant_raw) if isinstance(parsed, dict) else assistant_raw
        except (json.JSONDecodeError, TypeError):
            assistant_msg = assistant_raw
        if user_msg:
            messages.append(HumanMessage(content=str(user_msg)))
        if assistant_msg:
            messages.append(AIMessage(content=str(assistant_msg)))
    return messages


def _run(payload: dict, config: RunnableConfig | None = None) -> dict:
    """payload: {"input": str, "history": list, "role": str}. Returns
    {"type": ..., "response": ..., "citations"?: [...], "tool_calls": [...],
    "decision_context": {...}} -- the last two feed chains/hitl_chain.py's
    trigger evaluation without it needing to re-derive them."""
    user_input = (payload.get("input") or "").strip()
    history = payload.get("history") or []
    role = payload.get("role", "junior_analyst")

    if not user_input:
        return {"type": "clarification", "response": "Please enter a question."}

    tools = all_tools()
    tool_map = {t.name: t for t in tools}
    llm_with_tools = get_llm().bind_tools(tools)

    system_version = get_prompt_registry().get_active("agent_system")
    system_text = system_version.render(role=role)

    messages = [SystemMessage(content=system_text)]
    messages.extend(_history_to_messages(history))
    messages.append(HumanMessage(content=user_input))

    used_rag = False
    used_tool = False
    citations: list = []
    tool_call_log: list[dict] = []
    decision_context: dict = {}

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            ai_msg = llm_with_tools.invoke(messages, config=config)
        except Exception:
            logger.exception("Agent LLM invocation failed.")
            return {
                "type": "error",
                "response": "The assistant is temporarily unavailable. Please try again shortly.",
            }

        messages.append(ai_msg)
        tool_calls = getattr(ai_msg, "tool_calls", None) or []

        if not tool_calls:
            final_type = "rag_response" if used_rag else ("tool_response" if used_tool else "llm_response")
            result = {
                "type": final_type,
                "response": ai_msg.content,
                "tool_calls": tool_call_log,
                "decision_context": decision_context,
            }
            if used_rag:
                result["citations"] = citations
            return result

        for call in tool_calls:
            name = call["name"]
            args = call.get("args", {}) or {}
            tool_fn = tool_map.get(name)
            logger.info("Agent calling tool=%s args=%s role=%s", name, args, role)

            if name == "knowledge_retrieval":
                # Deliberately bypasses tool_fn.invoke()/its LLM-visible
                # args_schema: role and session_id are trusted server-side
                # context, never something the LLM should be able to set
                # itself (that would let a crafted tool-call argument
                # escalate RBAC access). Call the underlying function
                # directly with the authenticated role injected.
                try:
                    from tools.rag_tool import knowledge_retrieval as _raw_knowledge_retrieval
                    tool_output = _raw_knowledge_retrieval(
                        query=args.get("query", user_input),
                        filters=_build_doc_type_filters(args),
                        k=args.get("k", 5),
                        role=role,
                        session_id=payload.get("session_id", ""),
                    )
                except Exception as exc:
                    logger.exception("knowledge_retrieval failed.")
                    tool_output = {"error": f"knowledge_retrieval failed: {exc}"}
            elif tool_fn is None:
                tool_output = {"error": f"Unknown tool '{name}'"}
            else:
                try:
                    tool_output = tool_fn.invoke(args)
                except Exception as exc:
                    logger.exception("Tool '%s' raised an exception.", name)
                    tool_output = {"error": f"Tool '{name}' failed: {exc}"}

            tool_call_log.append({"name": name, "args": args, "output_preview": str(tool_output)[:300]})

            # Merge structured tool output into decision_context for the
            # HITL trigger engine (chains/hitl_chain.py) to evaluate against.
            if isinstance(tool_output, dict) and "error" not in tool_output:
                decision_context[name] = tool_output

            if name == "knowledge_retrieval" and isinstance(tool_output, dict):
                used_rag = True
                citations.extend(tool_output.get("citations", []))
            else:
                used_tool = True

            messages.append(
                ToolMessage(
                    content=json.dumps(tool_output, default=str, ensure_ascii=False),
                    tool_call_id=call["id"],
                )
            )

    logger.warning("Agent hit MAX_TOOL_ITERATIONS without a final answer.")
    return {
        "type": "error",
        "response": "I wasn't able to finish reasoning about this in time -- could you rephrase or simplify the question?",
    }


tool_chain = RunnableLambda(_run).with_config({"run_name": "tool_chain"})