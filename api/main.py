# FILE: api/main.py
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