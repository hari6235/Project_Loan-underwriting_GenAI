# Architecture

## Overview

The Loan Underwriting & Credit Risk Assistant is a LangChain-based system that
answers banking policy questions and evaluates loan applications. It combines
retrieval-augmented generation (RAG) over ingested banking documents,
deterministic underwriting tools, MCP-backed external tools, human-in-the-loop
(HITL) approval gates, role-based access control (RBAC) on retrieval, and a
YAML-driven prompt versioning layer.

The system extends the Week 6 RAG foundation with the production-grade
scaffolding required for Week 8: MCP tool interoperability, LCEL-based
LangChain orchestration, HITL gates, prompt version control, role-based RAG,
and an expanded evaluation suite.

## High-level components

```
Streamlit UI (app.py)
      │  HTTP
      ▼
FastAPI (api/main.py, api/routes.py, api/deps.py)
      │
      ├─ Auth & Role Resolution (rbac/)
      ├─ Prompt Manager (prompt_manager/, prompts/*.yaml)
      ├─ Guardrails (guardrails/) — PII detection, prompt injection, topic filter
      ├─ Chain Router (chains/router.py)
      │     ├─ RAG Chain (chains/rag_chain.py) ──> rag/ (loaders, chunkers,
      │     │                                        embeddings, hybrid
      │     │                                        retriever, reranker)
      │     │                                        │
      │     │                                        ▼
      │     │                                 Role-Based RAG Filter (rbac/filter.py)
      │     │
      │     ├─ Tool Chain (chains/tool_chain.py) ──> tools/ (DTI, credit
      │     │                                        score, policy flag,
      │     │                                        loan request, document,
      │     │                                        MCP-backed tools)
      │     │
      │     └─ HITL Chain (chains/hitl_chain.py) ──> hitl/ (manager, triggers,
      │                                              store, models)
      │
      ├─ MCP Client Layer (mcp/) ──> external/simulated tool servers
      ├─ Callbacks (callbacks/) — logging, LangSmith tracing, metrics
      ├─ Memory (memory/) — multi-turn conversation store (memory.db)
      └─ Eval Suite (eval/) — regression, drift, custom metrics, dashboard
```

## Request flow (chat)

1. `POST /chat` resolves the caller's role via `rbac` (`resolve_role`
   dependency in `api/deps.py`).
2. Guardrails run first: PII detection, prompt-injection detection, and
   banking-topic filtering (`guardrails/`).
3. `chains/router.py` classifies intent and routes to the appropriate LCEL
   chain (RAG, tool, or HITL), using `RunnableLambda` and
   `.with_fallbacks()` for graceful degradation to a fallback chain.
4. If the query needs document context, `chains/rag_chain.py` runs hybrid
   retrieval (`rag/retriever_bm25.py` + `rag/retriever_hybrid.py`), applies
   the role-based pre-retrieval filter (`rbac/filter.py`), reranks
   (`rag/reranker.py`), and contextualizes multi-turn follow-ups
   (`rag/contextualizer.py`).
5. If the query needs computation, `chains/tool_chain.py` invokes
   deterministic tools (`tools/dti_tool.py`, `tools/credit_score_tool.py`,
   `tools/policy_flag_tool.py`, `tools/loan_request_tool.py`) and/or
   MCP-backed tools via `mcp/client.py`.
6. Tool outputs are assembled into a `decision_context` dict and evaluated
   against `config/hitl_rules.yaml`. If a rule fires, the chain pauses and
   creates a task in the HITL store instead of returning a final answer.
7. `callbacks/logging.py`, `callbacks/tracing.py`, and `callbacks/metrics.py`
   attach to every chain invocation for structured logs, LangSmith traces,
   and metric emission.

## Data stores

| Store | Purpose |
|---|---|
| `data/vector_index/faiss/` | FAISS vector index for RAG document chunks |
| `memory.db` | Multi-turn conversation/session memory |
| `data/hitl_tasks.db` | Persistent HITL task queue (survives restarts) |
| `logs/interactions.log` | Interaction logging |
| `logs/rbac_audit.jsonl` | Audit trail of role-filtered retrievals |
| `reports/regression_history/` | Timestamped evaluation regression snapshots |

## Why this layout

Each production concern added in Week 8 (MCP, HITL, prompt versioning, RBAC,
drift/regression eval) is isolated in its own top-level package
(`mcp/`, `hitl/`, `prompt_manager/`, `rbac/`, `eval/`) rather than folded into
the chain code. This keeps the LCEL chains in `chains/` focused purely on
orchestration, with each concern independently testable
(see `tests/test_mcp_integration.py`, `tests/test_hitl_workflow.py`,
`tests/test_prompt_versioning.py`, `tests/test_role_based_rag.py`,
`tests/test_chains.py`).