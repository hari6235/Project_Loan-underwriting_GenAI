import streamlit as st
import requests
import json
import uuid

from guardrails.pii_detector import contains_pii
from guardrails.prompt_injection import detect_prompt_injection
from guardrails.topic_filter import is_banking_query

st.set_page_config(
    page_title="Loan Underwriting & Credit Risk Assistant",
    layout="wide"
)

st.title("🏦 Loan Underwriting & Credit Risk Assistant")

API_URL = "http://127.0.0.1:8000/chat"


# -------------------------
# SESSION STATE
# -------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# -------------------------
# CHAT UI
# -------------------------
st.header("💬 Banking Assistant Chatbot")

query = st.text_area("Ask a banking question")

if st.button("Submit Question"):

    if contains_pii(query):
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

        response = requests.post(API_URL, json=payload)

        if response.status_code == 200:

            data = response.json()

            st.session_state.chat_history.append(("user", query))
            st.session_state.chat_history.append(("bot", data["response"]))

        else:
            st.error(f"Backend Error: {response.text}")


# -------------------------
# CHAT DISPLAY
# -------------------------
st.subheader("Conversation")

for role, msg in st.session_state.chat_history:

    if role == "user":
        st.markdown(f"**You:** {msg}")
    else:
        st.json(msg)


# -------------------------
# RESET CHAT
# -------------------------
if st.button("Reset Chat"):

    st.session_state.chat_history = []

    try:
        requests.post(
            "http://127.0.0.1:8000/reset",
            params={"session_id": st.session_state.session_id}
        )
    except:
        pass

    st.success("Chat reset completed")