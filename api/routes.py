# FILE: api/routes.py

import json

from fastapi import APIRouter, Query
from pydantic import BaseModel

from core.chain import run_chain
from memory.memory_store import MemoryStore
from models.response_model import ChatResponse
from utils.logger import get_logger

logger = get_logger("api.routes")

router = APIRouter()
memory = MemoryStore(max_turns=10)


# -------------------------
# REQUEST MODEL
# -------------------------
class ChatRequest(BaseModel):
    session_id: str
    message: str


# -------------------------
# CHAT ENDPOINT
# -------------------------
@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):

    history = memory.get(req.session_id)

    result = run_chain(req.message, history)
    response = result["response"]
    response_type = result["type"]

    memory.add(
        req.session_id,
        req.message,
        json.dumps({"response": str(response), "type": response_type}, ensure_ascii=False),
    )

    logger.info("session_id=%s response_type=%s", req.session_id, response_type)

    return ChatResponse(
        response=response,
        session_id=req.session_id,
        history=memory.get(req.session_id),
    )


# -------------------------
# RESET
# -------------------------
@router.post("/reset")
def reset(session_id: str = Query(...)):

    memory.clear(session_id)
    logger.info("Memory cleared for session_id=%s", session_id)

    return {
        "message": "memory cleared",
        "session_id": session_id,
    }


# -------------------------
# HEALTH
# -------------------------
@router.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "loan-underwriting-ai",
    }