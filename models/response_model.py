from typing import Any, List, Optional
from pydantic import BaseModel


class BankingResponse(BaseModel):
    category: str
    answer: str
    confidence_score: float
    recommendation: str


# -------------------------
# API response schema for /chat endpoint
# -------------------------
class ChatResponse(BaseModel):
    response: Any
    session_id: str
    history: Optional[List[Any]] = []