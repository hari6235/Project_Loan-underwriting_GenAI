# FILE: api/routes.py
import json
import os
import uuid

from fastapi import APIRouter, Query, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel

from core.chain import run_chain
from memory.memory_store import MemoryStore
from models.response_model import ChatResponse
from utils.logger import get_logger

from rag.loaders import load_document
from rag.chunkers import chunk_documents
from rag.state import embedder, vector_store, refresh_bm25

from mcp.registry import get_registry as get_mcp_registry
from mcp.client import get_client as get_mcp_client, MCPInvocationError

from hitl.manager import get_manager as get_hitl_manager

from prompt_manager.registry import get_prompt_registry, PromptNotFoundError

from rbac.role_registry import get_role_registry

from api.deps import resolve_role

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
def chat(req: ChatRequest, role: str = Depends(resolve_role)):
    history = memory.get(req.session_id)
    result = run_chain(req.message, history, session_id=req.session_id, role=role)
    response = result["response"]
    response_type = result.get("type")
    citations = result.get("citations")
    hitl_task_id = result.get("hitl_task_id")
    hitl_severity = result.get("hitl_severity")

    memory.add(
        req.session_id,
        req.message,
        json.dumps({"response": str(response), "type": response_type}, ensure_ascii=False),
    )
    logger.info("session_id=%s role=%s response_type=%s", req.session_id, role, response_type)
    return ChatResponse(
        response=response,
        session_id=req.session_id,
        history=memory.get(req.session_id),
        type=response_type,
        citations=citations,
        hitl_task_id=hitl_task_id,
        hitl_severity=hitl_severity,
    )


# -------------------------
# RESET
# -------------------------
@router.post("/reset")
def reset(session_id: str = Query(...)):
    memory.clear(session_id)
    logger.info("Memory cleared for session_id=%s", session_id)
    return {"message": "memory cleared", "session_id": session_id}


# -------------------------
# HEALTH
# -------------------------
@router.get("/health")
def health():
    mcp_registry = get_mcp_registry()
    return {
        "status": "healthy",
        "service": "loan-underwriting-ai",
        "vector_store_loaded": vector_store.index is not None,
        "indexed_chunks": len(vector_store.index.docstore._dict) if vector_store.index else 0,
        "mcp_servers_registered": len(mcp_registry.servers),
        "hitl_pending_count": len(get_hitl_manager().pending()),
    }


# -------------------------
# INGEST
# -------------------------
_jobs: dict = {}


def _existing_source_names() -> set:
    if not vector_store.index:
        return set()
    return {d.metadata.get("source") for d in vector_store.index.docstore._dict.values()}


ALLOWED_DOC_TYPES = {"policy", "circular", "memo", "audit"}


@router.post("/ingest")
async def ingest(file: UploadFile = File(...), doc_type: str = Form(...)):
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"doc_type must be one of {sorted(ALLOWED_DOC_TYPES)}, got '{doc_type}'",
        )

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "progress": 0}

    os.makedirs("data/uploads", exist_ok=True)
    path = f"data/uploads/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())

    try:
        replaced = False
        if file.filename in _existing_source_names():
            vector_store.delete(file.filename)
            replaced = True
            logger.info("Ingest job=%s: existing source '%s' found, replacing", job_id, file.filename)

        docs = load_document(path)
        # Tag every loaded doc with its doc_type BEFORE chunking, so
        # chunk_documents()'s metadata spread ({**doc["metadata"], ...})
        # carries doc_type onto every resulting chunk. This is what
        # rbac/filter.py's role filter matches against at retrieval time --
        # without this, every chunk has no doc_type and the fail-closed
        # filter excludes it for every role.
        for d in docs:
            d["metadata"]["doc_type"] = doc_type

        chunks = chunk_documents(docs, strategy=os.getenv("CHUNK_STRATEGY", "recursive"))
        vector_store.add(chunks, embedder)
        vector_store.persist()
        refresh_bm25()

        _jobs[job_id] = {
            "status": "completed", "progress": 100,
            "chunks": len(chunks), "replaced_existing": replaced,
        }
        action = "Re-ingested (replaced existing)" if replaced else "Ingested"
        logger.info("Ingest job=%s completed: %s %d chunks from %s", job_id, action, len(chunks), file.filename)
    except Exception as e:
        _jobs[job_id] = {"status": "failed", "error": str(e)}
        logger.exception("Ingest job=%s failed", job_id)

    return {"job_id": job_id}


@router.get("/ingest/status/{job_id}")
async def ingest_status(job_id: str):
    return _jobs.get(job_id, {"status": "not_found"})


# -------------------------
# RETRIEVE (Week 6, debug-only, no LLM)
# -------------------------
@router.post("/retrieve")
async def retrieve(query: str, k: int = 5):
    chunks = vector_store.search(query, embedder, k=k)
    return {"chunks": chunks}


# -------------------------
# SOURCES (Week 6)
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
# EVALUATE (Week 6)
# -------------------------
@router.post("/evaluate")
async def evaluate():
    from eval.run_eval import run_full_eval
    return run_full_eval()


# =====================================================================
# WEEK 8: MCP
# =====================================================================
@router.get("/mcp/tools")
async def mcp_tools():
    """List all registered MCP tool servers with their capabilities and
    connection status (runs a fresh health check per server first)."""
    client = get_mcp_client()
    registry = get_mcp_registry()
    for server_id in registry.servers:
        client.health_check(server_id)
    return {"servers": registry.as_listing()}


class MCPInvokeRequest(BaseModel):
    tool_name: str
    params: dict = {}


@router.post("/mcp/invoke")
async def mcp_invoke(req: MCPInvokeRequest):
    client = get_mcp_client()
    try:
        result = client.invoke(req.tool_name, req.params)
        return result
    except MCPInvocationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =====================================================================
# WEEK 8: HITL
# =====================================================================
@router.get("/hitl/pending")
async def hitl_pending():
    manager = get_hitl_manager()
    tasks = manager.pending()
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "session_id": t.session_id,
                "triggered_rule_ids": t.triggered_rule_ids,
                "severity": t.severity,
                "recommendation": t.recommendation,
                "context": t.context,
                "confidence_score": t.confidence_score,
                "created_at": t.created_at,
                "expires_at": t.expires_at,
            }
            for t in tasks
        ]
    }


class HITLReviewRequest(BaseModel):
    decision: str  # "approve" | "reject"
    comments: str = ""
    decided_by: str = "unknown_reviewer"


@router.post("/hitl/review/{task_id}")
async def hitl_review(
    task_id: str,
    req: HITLReviewRequest,
    role: str = Depends(resolve_role),
):
    resolved_role = get_role_registry().get(role)
    if not resolved_role.can_request_hitl_override:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{role}' is not permitted to approve/reject HITL tasks (segregation of duties).",
        )

    manager = get_hitl_manager()
    try:
        task = manager.review(task_id, decision=req.decision, decided_by=req.decided_by or role, comments=req.comments)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "decided_by": task.decided_by,
        "decided_at": task.decided_at,
        "decision_comments": task.decision_comments,
    }


# =====================================================================
# WEEK 8: Prompt version control
# =====================================================================
@router.get("/prompts")
async def list_prompts():
    return {"prompts": get_prompt_registry().list_prompts()}


@router.get("/prompts/{name}/history")
async def prompt_history(name: str):
    try:
        return {"name": name, "history": get_prompt_registry().history(name)}
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


class PromptActivateRequest(BaseModel):
    version: str


@router.post("/prompts/{name}/activate")
async def activate_prompt(name: str, req: PromptActivateRequest):
    try:
        return get_prompt_registry().activate(name, req.version)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =====================================================================
# WEEK 8: RBAC
# =====================================================================
@router.get("/roles")
async def list_roles():
    return {"roles": get_role_registry().list_roles()}


@router.get("/auth/context")
async def auth_context(role: str = Depends(resolve_role)):
    """role is already fail-closed-resolved to a valid registry entry by
    resolve_role() (an unrecognised X-User-Role header becomes
    'junior_analyst', never the raw unrecognised string), so this always
    reflects a real, permitted role -- never the registry's internal
    '__default__' fallback object directly."""
    resolved = get_role_registry().get(role)
    return {
        "role": resolved.name,
        "allowed_doc_types": resolved.allowed_doc_types,
        "denied_doc_types": resolved.denied_doc_types,
        "can_request_hitl_override": resolved.can_request_hitl_override,
    }


# =====================================================================
# WEEK 8: Extended evaluation
# =====================================================================
@router.post("/eval/regression")
async def eval_regression():
    from eval.regression_suite import run_regression_suite
    return run_regression_suite()


@router.post("/eval/drift")
async def eval_drift():
    from eval.drift import run_drift_check
    return run_drift_check()