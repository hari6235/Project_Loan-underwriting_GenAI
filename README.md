# Loan Underwriting & Credit Risk Assistant

This repository contains a LangChain-based assistant for loan underwriting and credit-risk support. The current implementation combines a FastAPI backend, a Streamlit frontend, retrieval-augmented generation (RAG) over uploaded banking documents, deterministic underwriting tools, MCP-backed tools, human-in-the-loop approval workflows, RBAC, and automated evaluation.

## What is included in the current build

- A production-style FastAPI service with chat, health, ingest, retrieval, HITL, prompt-management, RBAC, and evaluation endpoints
- A Streamlit UI with separate tabs for chat, document management, HITL approvals, prompt versioning, MCP tools, and eval dashboards
- RAG over uploaded documents (PDF, DOCX, HTML, TXT, CSV) with chunking, embedding, BM25/hybrid retrieval, and reranking
- Guardrails for PII detection, prompt injection prevention, and banking-topic filtering
- Human-in-the-loop review for high-risk or policy-sensitive actions
- Role-based access control with audit logging and segregation-of-duties checks
- Prompt versioning and rollback from the UI
- LangSmith tracing and evaluation support via regression, drift, and dashboard workflows

## Project layout

```text
app.py                  # Streamlit frontend
api/                    # FastAPI routes and app setup
chains/                 # Orchestration for tool/RAG/HITL flows
rag/                    # Loaders, chunkers, embeddings, retrieval, reranking
tools/                  # Credit score, DTI, document verification, RAG tools
mcp/                    # MCP registry, client, adapter, simulated handlers
hitl/                   # HITL task model, store, trigger engine, manager
rbac/                   # Role registry, validator, audit, filtering
eval/                   # Golden-set eval, regression suite, drift check, dashboard
prompts/                # Prompt YAML and versioned prompt definitions
config/                 # HITL rules, prompt config, MCP server config
```

## Prerequisites

- Python 3.10+
- An OpenAI or Anthropic API key (depending on the model provider configured)
- Internet access for external LLM calls and optional LangSmith tracing

## Environment setup

Create a `.env` file in the project root with values such as:

```bash
OPENAI_API_KEY=your-openai-key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.2
API_BASE_URL=http://127.0.0.1:8000

# Optional LangSmith tracing
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=loan_underwriting_assistant
```

If you use VS Code and see import diagnostics, set the interpreter to the project virtual environment at `venv/bin/python` and reload the window.

## Quick start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend in a second terminal:

```bash
streamlit run app.py
```

Then open `http://localhost:8501`.

## Main workflows

- Chat with the underwriting assistant
- Upload and index policy or support documents from the UI
- Ask retrieval-based questions over the indexed knowledge base
- Review pending HITL approvals for high-risk actions
- Switch roles from the sidebar to test RBAC behavior
- Roll back prompt versions from the prompt management tab
- Trigger evaluation flows from the eval dashboard or API endpoints

## API highlights

- `POST /chat` – Send a user message and receive a response
- `POST /reset` – Clear memory for a session
- `GET /health` – Check service health and basic status
- `POST /ingest` – Upload a document for ingestion into the knowledge base
- `GET /ingest/status/{job_id}` – Check document-ingestion progress
- `GET /sources` and `DELETE /sources/{doc_id}` – Inspect or remove indexed sources
- `GET /hitl/pending` and `POST /hitl/review/{task_id}` – Review human approval tasks
- `GET /prompts` and `POST /prompts/{name}/activate` – Manage prompt versions
- `GET /mcp/tools` and `POST /mcp/invoke` – Inspect and invoke MCP-backed tools
- `POST /eval/regression` and `POST /eval/drift` – Run evaluation workflows

## Testing and evaluation

Run the test suite:

```bash
pytest
```

Run health checks or evaluation endpoints from the API once the backend is running:

```bash
curl http://localhost:8000/health
```

## Notes

- The app stores session memory and HITL state locally in the project workspace
- Uploaded documents are stored under `data/uploads/`
- Audit logs and evaluation reports are written under `logs/` and `reports/`
- LangSmith tracing is active when the relevant environment variables are configured

## License

This project is intended for educational and demonstration purposes.

---

## 📞 Support

For issues or questions:
1. Check logs: `cat logs/interactions.log`
2. Review API docs: `http://localhost:8000/docs`
3. Test endpoints manually in Streamlit UI
4. Verify `.env` configuration
