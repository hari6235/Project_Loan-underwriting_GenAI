# FILE: models/response_model.py
from typing import Any, List, Optional
from pydantic import BaseModel


class BankingResponse(BaseModel):
    category: str
    answer: str
    confidence_score: float
    recommendation: str


class Citation(BaseModel):
    chunk_id: Optional[str] = None
    doc_name: Optional[str] = None
    page: Optional[int] = None
    score: Optional[float] = None
    text: str


# -------------------------
# API response schema for /chat endpoint
# -------------------------
class ChatResponse(BaseModel):
    response: Any
    session_id: str
    history: Optional[List[Any]] = []
    type: Optional[str] = None
    citations: Optional[List[Citation]] = None
    hitl_task_id: Optional[str] = None
    hitl_severity: Optional[str] = None