# FILE: api/routes.py
import json
import os
import uuid
from fastapi import APIRouter, Query, UploadFile, File
from pydantic import BaseModel

from core.chain import run_chain
from memory.memory_store import MemoryStore
from models.response_model import ChatResponse
from utils.logger import get_logger

from rag.loaders import load_document
from rag.chunkers import chunk_documents
from rag.state import embedder, vector_store, refresh_bm25

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
    response_type = result.get("type")
    citations = result.get("citations")  # present only when the RAG tool was invoked

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
        type=response_type,
        citations=citations,
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
        "vector_store_loaded": vector_store.index is not None,
        "indexed_chunks": len(vector_store.index.docstore._dict) if vector_store.index else 0,
    }


# -------------------------
# INGEST (new)
# -------------------------
_jobs: dict = {}  # in-memory job tracker; fine for a single-process dev setup


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "progress": 0}

    os.makedirs("data/uploads", exist_ok=True)
    path = f"data/uploads/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())

    try:
        docs = load_document(path)
        chunks = chunk_documents(docs, strategy=os.getenv("CHUNK_STRATEGY", "recursive"))
        vector_store.add(chunks, embedder)
        vector_store.persist()
        refresh_bm25()  # keep the sparse retriever in sync with the newly ingested chunks
        _jobs[job_id] = {"status": "completed", "progress": 100, "chunks": len(chunks)}
        logger.info("Ingest job=%s completed: %d chunks from %s", job_id, len(chunks), file.filename)
    except Exception as e:
        _jobs[job_id] = {"status": "failed", "error": str(e)}
        logger.exception("Ingest job=%s failed", job_id)

    return {"job_id": job_id}


@router.get("/ingest/status/{job_id}")
async def ingest_status(job_id: str):
    return _jobs.get(job_id, {"status": "not_found"})


# -------------------------
# RETRIEVE (new, debug-only, no LLM)
# -------------------------
@router.post("/retrieve")
async def retrieve(query: str, k: int = 5):
    chunks = vector_store.search(query, embedder, k=k)
    return {"chunks": chunks}


# -------------------------
# SOURCES (new)
# -------------------------
@router.get("/sources")
async def list_sources():
    if not vector_store.index:
        return {"sources": []}
    counts: dict = {}
    for d in vector_store.index.docstore._dict.values():
        src = d.metadata.get("source")
        counts[src] = counts.get(src, 0) + 1
    return {"sources": [{"doc_id": k, "chunk_count": v} for k, v in counts.items()]}


@router.delete("/sources/{doc_id}")
async def delete_source(doc_id: str):
    vector_store.delete(doc_id)
    vector_store.persist()
    refresh_bm25()
    logger.info("Deleted source=%s and refreshed BM25 index", doc_id)
    return {"deleted": doc_id}


# -------------------------
# EVALUATE (new)
# -------------------------
@router.post("/evaluate")
async def evaluate():
    from eval.run_eval import run_full_eval
    return run_full_eval()