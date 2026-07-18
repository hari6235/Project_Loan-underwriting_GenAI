# FILE: api/main.py
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
               # must run before importing api.routes, which imports rag.state
               # (rag/state.py builds OpenAIEmbeddings() at module load time).
               # Path resolved relative to this file (api/main.py -> project root),
               # not cwd, so it works regardless of the directory uvicorn was launched from.

from fastapi import FastAPI

from api.routes import router

app = FastAPI(
    title="Loan Underwriting API",
    version="2.0",  # Week 8: MCP, LCEL orchestration, HITL, prompt versioning, RBAC, extended eval
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "Loan Underwriting API is running",
        "docs": "/docs",
        "health": "/health",
    }