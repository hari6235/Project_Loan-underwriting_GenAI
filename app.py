from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
               # must run before anything that constructs an OpenAI client at import time
               # (rag/state.py builds OpenAIEmbeddings() at module load, and eval_tab's
               # render_eval_dashboard() -> eval.regression_suite -> rag.state runs on
               # EVERY Streamlit rerun regardless of which tab is visually active).
               # Path resolved relative to this file, not cwd, so it works regardless
               # of the directory Streamlit was launched from.

import streamlit as st
import requests
import json
import uuid
import time
from guardrails.pii_detector import contains_pii
from guardrails.prompt_injection import detect_prompt_injection
from guardrails.topic_filter import is_banking_query

st.set_page_config(
    page_title="Loan Underwriting & Credit Risk Assistant",
    layout="wide"
)
st.title("🏦 Loan Underwriting & Credit Risk Assistant")

import os
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
CHAT_URL = f"{API_BASE}/chat"
RESET_URL = f"{API_BASE}/reset"
INGEST_URL = f"{API_BASE}/ingest"
INGEST_STATUS_URL = f"{API_BASE}/ingest/status"
SOURCES_URL = f"{API_BASE}/sources"
ROLES_URL = f"{API_BASE}/roles"
AUTH_CONTEXT_URL = f"{API_BASE}/auth/context"
HITL_PENDING_URL = f"{API_BASE}/hitl/pending"
HITL_REVIEW_URL = f"{API_BASE}/hitl/review"
PROMPTS_URL = f"{API_BASE}/prompts"
MCP_TOOLS_URL = f"{API_BASE}/mcp/tools"

# -------------------------
# SESSION STATE
# -------------------------
if "chat_history" not in st.session_state:
    # each entry: (role, message, citations_or_None)
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# -------------------------
# ROLE SELECTOR (Section 5.2: "role selector" in the UI)
# -------------------------
if "user_role" not in st.session_state:
    st.session_state.user_role = "junior_analyst"

with st.sidebar:
    st.subheader("Session")
    try:
        roles_resp = requests.get(ROLES_URL, timeout=5)
        role_names = [r["name"] for r in roles_resp.json().get("roles", [])] if roles_resp.status_code == 200 else []
    except requests.exceptions.RequestException:
        role_names = []
    if not role_names:
        role_names = ["junior_analyst", "senior_underwriter", "credit_head", "auditor"]

    st.session_state.user_role = st.selectbox(
        "Acting as role", role_names,
        index=role_names.index(st.session_state.user_role) if st.session_state.user_role in role_names else 0,
    )
    st.caption(f"Session ID: `{st.session_state.session_id[:8]}...`")

# -------------------------
# TABS: CHAT | DOCUMENT MANAGEMENT
# -------------------------
chat_tab, docs_tab, hitl_tab, prompts_tab, mcp_tab, eval_tab = st.tabs([
    "💬 Chat", "📁 Document Management", "✅ HITL Approvals",
    "📝 Prompt Versions", "🔌 MCP Tools", "📊 Eval Dashboard",
])

# =========================================================
# CHAT TAB
# =========================================================
with chat_tab:
    st.header("💬 Banking Assistant Chatbot")
    query = st.text_area("Ask a banking question")

    if st.button("Submit Question"):
        if not query or not query.strip():
            st.warning("Please enter a question before submitting.")
        elif contains_pii(query):
            st.error("PII Detected. Please remove personal information.")
        elif detect_prompt_injection(query):
            st.error("Prompt Injection Attempt Detected.")
        elif not is_banking_query(query):
            st.error("Please ask banking/loan/credit related questions only.")
        else:
            payload = {
                "session_id": st.session_state.session_id,
                "message": query
            }
            try:
                response = requests.post(
                    CHAT_URL, json=payload,
                    headers={"X-User-Role": st.session_state.user_role},
                )
            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach backend: {e}")
            else:
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        st.error(f"Backend did not return valid JSON: {response.text}")
                    else:
                        st.session_state.chat_history.append(("user", query, None))
                        if data.get("type") == "pending_approval":
                            st.session_state.chat_history.append((
                                "bot",
                                f"⏸️ {data.get('response', '')} (task_id: {data.get('hitl_task_id')}, "
                                f"severity: {data.get('hitl_severity')}) -- see the HITL Approvals tab.",
                                None,
                            ))
                        else:
                            st.session_state.chat_history.append((
                                "bot",
                                data.get("response", ""),
                                data.get("citations"),  # None for non-RAG responses
                            ))
                else:
                    st.error(f"Backend Error: {response.text}")

    # -------------------------
    # CHAT DISPLAY
    # -------------------------
    st.subheader("Conversation")
    for role, msg, citations in st.session_state.chat_history:
        if role == "user":
            st.markdown(f"**You:** {msg}")
        else:
            # Bot responses are plain text from the LLM, not JSON.
            # Only use st.json if the message happens to be structured data.
            if isinstance(msg, (dict, list)):
                st.json(msg)
            else:
                try:
                    parsed = json.loads(msg)
                    st.json(parsed)
                except (json.JSONDecodeError, TypeError):
                    st.markdown(f"**Bot:** {msg}")

            # Clickable/expandable citations -- satisfies "clicking a citation
            # surfaces the exact source chunk" from the non-functional spec.
            if citations:
                st.caption(f"📎 {len(citations)} source citation(s)")
                for i, c in enumerate(citations, start=1):
                    doc_name = c.get("doc_name") or "unknown document"
                    page = c.get("page")
                    score = c.get("score")
                    label = f"[{i}] {doc_name}" + (f" — page {page}" if page else "")
                    with st.expander(label):
                        if score is not None:
                            st.caption(f"Relevance score: {score:.4f}")
                        st.write(c.get("text", ""))
            st.divider()

    # -------------------------
    # RESET CHAT
    # -------------------------
    if st.button("Reset Chat"):
        st.session_state.chat_history = []
        try:
            requests.post(RESET_URL, params={"session_id": st.session_state.session_id})
        except requests.exceptions.RequestException:
            pass
        st.success("Chat reset completed")

# =========================================================
# DOCUMENT MANAGEMENT TAB
# =========================================================
with docs_tab:
    st.header("📁 Knowledge Base — Document Management")

    # --- Upload ---
    st.subheader("Upload a document")
    st.caption("Uploading a file with the same name as an existing document will replace it (old chunks removed, new version re-indexed).")
    uploaded_file = st.file_uploader(
        "Policy manuals, RBI circulars, memos (PDF, DOCX, HTML, TXT, CSV)",
        type=["pdf", "docx", "html", "htm", "txt", "csv"],
    )
    doc_type = st.selectbox(
        "Document type (drives role-based retrieval access)",
        ["policy", "circular", "memo", "audit"],
    )

    if uploaded_file is not None and st.button("Ingest Document"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        data = {"doc_type": doc_type}
        try:
            resp = requests.post(INGEST_URL, files=files, data=data)
        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach backend: {e}")
        else:
            if resp.status_code != 200:
                st.error(f"Ingest request failed: {resp.text}")
            else:
                job_id = resp.json().get("job_id")
                status_placeholder = st.empty()
                progress_bar = st.progress(0)

                # Poll /ingest/status/{job_id} until completed or failed
                for _ in range(60):  # ~60s timeout at 1s intervals
                    status_resp = requests.get(f"{INGEST_STATUS_URL}/{job_id}")
                    status_data = status_resp.json()
                    state = status_data.get("status")

                    if state == "running":
                        status_placeholder.info("Ingesting... (loading → chunking → embedding)")
                        progress_bar.progress(50)
                    elif state == "completed":
                        progress_bar.progress(100)
                        verb = "Updated" if status_data.get("replaced_existing") else "Ingested"
                        status_placeholder.success(
                            f"✅ {verb} '{uploaded_file.name}' — {status_data.get('chunks')} chunks indexed."
                        )
                        break
                    elif state == "failed":
                        status_placeholder.error(f"❌ Ingestion failed: {status_data.get('error')}")
                        break
                    time.sleep(1)
                else:
                    status_placeholder.warning("Still processing — refresh the page shortly to check status.")

    st.divider()

    # --- Indexed sources list ---
    st.subheader("Indexed documents")
    if st.button("🔄 Refresh list"):
        st.rerun()

    try:
        sources_resp = requests.get(SOURCES_URL)
        sources = sources_resp.json().get("sources", []) if sources_resp.status_code == 200 else []
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        sources = []

    if not sources:
        st.info("No documents indexed yet. Upload one above.")
    else:
        for src in sources:
            col1, col2, col3 = st.columns([4, 2, 1])
            col1.write(src.get("doc_id"))
            col2.write(f"{src.get('chunk_count')} chunks")
            if col3.button("🗑️ Delete", key=f"del_{src.get('doc_id')}"):
                try:
                    del_resp = requests.delete(f"{SOURCES_URL}/{src.get('doc_id')}")
                    if del_resp.status_code == 200:
                        st.success(f"Deleted {src.get('doc_id')}")
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {del_resp.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not reach backend: {e}")

# =========================================================
# HITL APPROVALS TAB (Section 5.2 requirement)
# =========================================================
with hitl_tab:
    st.header("✅ Human-in-the-Loop Approvals")
    st.caption(
        "Actions that trip a configured trigger rule (large loan amount, policy override, "
        "low credit score, DTI exception) pause here for review before being finalised."
    )

    # The pending queue itself is intentionally the SAME for every role (anyone
    # should be able to see what's pending) -- only the ability to act on it is
    # role-gated. Surface that gating clearly UP FRONT here, so switching roles
    # in the sidebar has a visible effect on this tab even before you click
    # anything (previously the only signal was a 403 error after clicking).
    try:
        auth_resp = requests.get(AUTH_CONTEXT_URL, headers={"X-User-Role": st.session_state.user_role}, timeout=5)
        can_approve = auth_resp.json().get("can_request_hitl_override", False) if auth_resp.status_code == 200 else False
    except requests.exceptions.RequestException:
        can_approve = False

    if can_approve:
        st.success(f"✅ Role **{st.session_state.user_role}** can approve/reject HITL tasks.")
    else:
        st.warning(
            f"👁️ Role **{st.session_state.user_role}** can view this queue but cannot approve/reject "
            f"(segregation of duties — switch to a role with override permission, e.g. `credit_head`, to act on tasks)."
        )

    if st.button("🔄 Refresh pending tasks"):
        st.rerun()

    try:
        pending_resp = requests.get(HITL_PENDING_URL, timeout=5)
        tasks = pending_resp.json().get("tasks", []) if pending_resp.status_code == 200 else []
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        tasks = []

    if not tasks:
        st.info("No pending approvals.")
    else:
        for task in tasks:
            with st.expander(
                f"[{task['severity'].upper()}] {task['task_id'][:8]}... -- {', '.join(task['triggered_rule_ids'])}"
            ):
                st.markdown("**Proposed recommendation:**")
                st.write(task["recommendation"])
                if task.get("confidence_score") is not None:
                    st.caption(f"AI confidence: {task['confidence_score']:.2f}")
                st.markdown("**Supporting context (tool outputs):**")
                st.json(task.get("context", {}))
                st.caption(f"Created: {task['created_at']} · Expires: {task.get('expires_at', 'n/a')}")

                comments = st.text_area("Review comments", key=f"comments_{task['task_id']}", disabled=not can_approve)
                col_a, col_r = st.columns(2)
                if col_a.button("✅ Approve", key=f"approve_{task['task_id']}", disabled=not can_approve):
                    resp = requests.post(
                        f"{HITL_REVIEW_URL}/{task['task_id']}",
                        json={"decision": "approve", "comments": comments, "decided_by": st.session_state.user_role},
                        headers={"X-User-Role": st.session_state.user_role},
                    )
                    if resp.status_code == 200:
                        st.success("Approved.")
                        st.rerun()
                    elif resp.status_code == 403:
                        st.error(f"Role '{st.session_state.user_role}' cannot approve HITL tasks (needs can_request_hitl_override).")
                    else:
                        st.error(resp.text)
                if col_r.button("❌ Reject", key=f"reject_{task['task_id']}", disabled=not can_approve):
                    resp = requests.post(
                        f"{HITL_REVIEW_URL}/{task['task_id']}",
                        json={"decision": "reject", "comments": comments, "decided_by": st.session_state.user_role},
                        headers={"X-User-Role": st.session_state.user_role},
                    )
                    if resp.status_code == 200:
                        st.warning("Rejected.")
                        st.rerun()
                    elif resp.status_code == 403:
                        st.error(f"Role '{st.session_state.user_role}' cannot reject HITL tasks (needs can_request_hitl_override).")
                    else:
                        st.error(resp.text)


# =========================================================
# PROMPT VERSIONS TAB (Section 5.2 requirement)
# =========================================================
with prompts_tab:
    st.header("📝 Prompt Version Control")
    try:
        prompts_resp = requests.get(PROMPTS_URL, timeout=5)
        prompts = prompts_resp.json().get("prompts", []) if prompts_resp.status_code == 200 else []
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        prompts = []

    if not prompts:
        st.info("No prompt templates found.")
    else:
        names = [p["name"] for p in prompts]
        selected = st.selectbox("Prompt template", names)
        if selected:
            hist_resp = requests.get(f"{PROMPTS_URL}/{selected}/history")
            history_data = hist_resp.json().get("history", []) if hist_resp.status_code == 200 else []
            for v in history_data:
                label = f"v{v['version']}" + (" (ACTIVE)" if v["is_active"] else "")
                with st.expander(label):
                    st.write(f"**Author:** {v['author']}")
                    st.write(f"**Changelog:** {v['changelog']}")
                    st.write(f"**Model compatibility:** {', '.join(v['model_compatibility'])}")
                    st.write(f"**Input variables:** {', '.join(v['input_variables'])}")
                    if not v["is_active"]:
                        if st.button(f"⏪ Roll back to v{v['version']}", key=f"activate_{selected}_{v['version']}"):
                            act_resp = requests.post(f"{PROMPTS_URL}/{selected}/activate", json={"version": v["version"]})
                            if act_resp.status_code == 200:
                                st.success(f"Rolled back '{selected}' to v{v['version']}.")
                                st.rerun()
                            else:
                                st.error(act_resp.text)


# =========================================================
# MCP TOOLS TAB
# =========================================================
with mcp_tab:
    st.header("🔌 MCP Tool Servers")
    try:
        mcp_resp = requests.get(MCP_TOOLS_URL, timeout=5)
        servers = mcp_resp.json().get("servers", []) if mcp_resp.status_code == 200 else []
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        servers = []

    for server in servers:
        status_icon = "🟢" if server["status"] == "healthy" else ("🔴" if server["status"] == "unhealthy" else "⚪")
        with st.expander(f"{status_icon} {server['server_id']} ({server['mode']})"):
            st.write(server["description"])
            for t in server["tools"]:
                st.markdown(f"- **{t['name']}**: {t['description']}")


# =========================================================
# EVAL DASHBOARD TAB (Section 5.2 requirement)
# =========================================================
with eval_tab:
    from eval.dashboard import render_eval_dashboard
    render_eval_dashboard()