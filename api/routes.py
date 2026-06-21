# FILE: api/routes.py

from fastapi import APIRouter, Query
from pydantic import BaseModel
import json

from services.llm_service import ask_llm, run_tools
from memory.memory_store import MemoryStore

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
@router.post("/chat")
def chat(req: ChatRequest):

    message = req.message.strip()
    message_lower = message.lower()

    # -------------------------
    # GET HISTORY (SAFE HANDLING)
    # -------------------------
    history = memory.get(req.session_id)

    context_text = ""

    # FIX: history is dict format, not tuple
    for h in history:

        user_msg = h.get("user", "")

        assistant_msg = h.get("assistant", "")

        context_text += f"User: {user_msg}\nAssistant: {assistant_msg}\n"

    # -------------------------
    # TOOL ROUTE
    # -------------------------
    if (
        "credit score" in message_lower
        or "dti" in message_lower
        or "document" in message_lower
    ):
        response = run_tools(message)
        response_type = "tool"

    # -------------------------
    # LLM ROUTE WITH CONTEXT
    # -------------------------
    else:

        prompt = f"""
You are a loan underwriting AI assistant.

Use conversation history properly.

Conversation:
{context_text}

User:
{message}

Answer clearly and simply.
"""

        response = ask_llm(prompt)
        response_type = "llm"

    # -------------------------
    # SAVE MEMORY (FIXED FORMAT)
    # -------------------------
    memory.add(
        req.session_id,
        message,
        json.dumps({
            "response": str(response),
            "type": response_type
        }, ensure_ascii=False)
    )

    # -------------------------
    # RETURN
    # -------------------------
    return {
        "response": response,
        "session_id": req.session_id,
        "history": memory.get(req.session_id)
    }


# -------------------------
# RESET
# -------------------------
@router.post("/reset")
def reset(session_id: str = Query(...)):

    memory.clear(session_id)

    return {
        "message": "memory cleared",
        "session_id": session_id
    }


# -------------------------
# HEALTH
# -------------------------
@router.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "loan-underwriting-ai"
    }