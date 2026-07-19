# Deployment

> **Note:** This project intentionally does not use Docker/docker-compose.
> It is deployed and run as two local processes — a FastAPI backend and a
> Streamlit frontend — communicating over HTTP. This document covers that
> deployment path.

## Prerequisites

- Python 3.10+
- An OpenAI or Anthropic API key (see `services/llm_service.py` for which
  provider is active)
- Internet access for LLM calls and optional LangSmith tracing

## Environment configuration

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.2
API_BASE_URL=http://127.0.0.1:8000

# Optional LangSmith tracing
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=loan_underwriting_assistant

# MCP server auth (only needed if a server's mode is switched to "http")
CREDIT_BUREAU_API_KEY=
INCOME_VERIFY_API_KEY=
PROPVAL_API_KEY=
```

`app.py` loads this file explicitly via `load_dotenv()` before any module
that constructs an LLM/embeddings client at import time, so it works
regardless of the working directory Streamlit is launched from.

## Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the services

**Backend (FastAPI):**

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger docs are available at `http://127.0.0.1:8000/docs` once running,
covering all endpoints listed in the individual component docs
(`mcp_integration.md`, `hitl_workflows.md`, `prompt_management.md`,
`rbac.md`, `eval_methodology.md`).

**Frontend (Streamlit), in a second terminal:**

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

## Data initialization

- The FAISS vector index is built/populated via `POST /ingest` (or the
  "Documents" tab in the Streamlit UI) — no seed data is required to start
  the backend, but RAG answers will have no context until documents are
  ingested.
- `data/hitl_tasks.db` and `memory.db` are created automatically on first
  run if they don't exist.
- `config/mcp_servers.yaml` servers run in `mode: simulated` by default, so
  no external credentials are required to exercise the MCP integration
  end-to-end (see `mcp_integration.md`).

## Health check

```bash
curl http://127.0.0.1:8000/health
```

## Logs and audit trails

- `logs/interactions.log` — general interaction log.
- `logs/rbac_audit.jsonl` — append-only audit trail of every role-filtered
  retrieval (see `rbac.md`).
- `reports/regression_history/` — timestamped evaluation snapshots produced
  by `POST /eval/regression`.

## Known limitations of this deployment path

- No container orchestration: the backend and frontend must be started as
  two separate local processes, and there is no `docker-compose up` single
  command for this project (a deliberate scope decision for this
  submission).
- No process manager/supervisor is configured; for anything beyond local
  development, `uvicorn` should be run behind a process manager (e.g.
  systemd, supervisord) and Streamlit behind a reverse proxy.