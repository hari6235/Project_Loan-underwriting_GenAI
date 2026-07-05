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

API_BASE = "http://127.0.0.1:8000"
CHAT_URL = f"{API_BASE}/chat"
RESET_URL = f"{API_BASE}/reset"
INGEST_URL = f"{API_BASE}/ingest"
INGEST_STATUS_URL = f"{API_BASE}/ingest/status"
SOURCES_URL = f"{API_BASE}/sources"

# -------------------------
# SESSION STATE
# -------------------------
if "chat_history" not in st.session_state:
    # each entry: (role, message, citations_or_None)
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# -------------------------
# TABS: CHAT | DOCUMENT MANAGEMENT
# -------------------------
chat_tab, docs_tab = st.tabs(["💬 Chat", "📁 Document Management"])

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
                response = requests.post(CHAT_URL, json=payload)
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

    if uploaded_file is not None and st.button("Ingest Document"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        try:
            resp = requests.post(INGEST_URL, files=files)
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