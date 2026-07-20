# Loan Underwriting & Credit Risk Assistant

This repository contains a full-stack assistant for loan underwriting and credit-risk support. The current implementation combines a FastAPI backend, a Streamlit frontend, retrieval-augmented generation (RAG) over uploaded banking documents, deterministic underwriting tools, MCP-backed integrations, human-in-the-loop approval workflows, RBAC, and automated evaluation.

## What is included in the latest build

- A FastAPI service with endpoints for chat, health checks, document ingestion, retrieval, HITL review, prompt management, RBAC context, MCP tools, and evaluation
- A Streamlit UI with dedicated tabs for chat, document management, HITL approvals, prompt versioning, MCP tools, and the evaluation dashboard
- RAG over uploaded policy and banking documents (PDF, DOCX, HTML, TXT, CSV) using chunking, embedding, BM25/hybrid retrieval, and reranking
- Guardrails for PII detection, prompt injection prevention, and banking-topic filtering
- Human-in-the-loop review for high-risk or policy-sensitive underwriting actions
- Role-based access control with audit logging and segregation-of-duties checks
- Prompt versioning and rollback from the UI
- LangSmith tracing and evaluation support through regression, drift, and dashboard workflows

## Project structure

```text
app.py                  # Streamlit frontend
api/                    # FastAPI routes and service wiring
chains/                 # Orchestration for tool, RAG, and HITL flows
rag/                    # Loaders, chunkers, embeddings, retrieval, reranking
tools/                  # Credit score, DTI, policy flag, document, and RAG tools
mcp/                    # MCP registry, client, adapter, and simulated handlers
hitl/                   # HITL task model, store, trigger engine, and manager
rbac/                   # Role registry, validator, audit, and filtering
eval/                   # Golden-set eval, regression suite, drift checks, and dashboard
prompts/                # Prompt YAML definitions and versioned prompt configuration
config/                 # HITL rules, role config, and MCP server configuration
data/                   # Few-shot examples, applicant store, vector index assets
reports/                # Evaluation and regression reports
```

## Prerequisites

- Python 3.10+
- An OpenAI or Anthropic API key (depending on the configured provider)
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

## Key workflows

- Chat with the underwriting assistant
- Upload and index policy or support documents from the UI
- Ask retrieval-based questions over the indexed knowledge base
- Review pending HITL approvals for high-risk actions
- Switch roles from the sidebar to test RBAC behavior
- Roll back prompt versions from the prompt management tab
- Trigger evaluation flows from the evaluation dashboard or API endpoints

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

Health checks can be verified once the backend is running:

```bash
curl http://localhost:8000/health
```

### Comprehensive Test Suite

For complete test documentation, coverage details, and evaluation instructions, see:
- **[TESTING.md](TESTING.md)** - Test suite overview and evaluation guide
- **[tests/TEST_GUIDE.md](tests/TEST_GUIDE.md)** - Detailed test documentation (130+ tests)
- **[tests/README.md](tests/README.md)** - Quick reference guide

**Test Coverage:**
- 48 new comprehensive functional tests
- 25+ API integration tests
- 96+ existing unit tests
- **130+ total tests** covering all major features

Run tests with:
```bash
# All tests
python -m pytest tests/ -v

# Specific test suite
python -m pytest tests/test_functional_suite.py -v

# API tests (requires backend)
python -m pytest tests/test_api_integration.py -v

# With coverage report
pytest --cov=. --cov-report=html
```


## Notes

- Session memory and HITL state are stored locally in the workspace
- Uploaded documents are stored under `data/uploads/`
- Audit logs and evaluation reports are written under `logs/` and `reports/`
- LangSmith tracing is active when the relevant environment variables are configured

## License

This project is intended for educational and demonstration purposes.

---

## Support

For issues or questions:
1. Review the logs in `logs/interactions.log`
2. Open the API docs at `http://localhost:8000/docs`
3. Test the flows through the Streamlit UI
4. Verify the `.env` configuration
