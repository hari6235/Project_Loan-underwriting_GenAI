import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

from tools.langchain_tools import (
    credit_score_analyzer,
    dti_calculator,
    document_verification
)

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)

# -------------------------
# LLM CALL
# -------------------------
def ask_llm(query: str):

    response = llm.invoke(query)

    return {
        "type": "llm_response",
        "response": response.content
    }


# -------------------------
# TOOL ROUTER (FIXED SCHEMA MAPPING)
# -------------------------
def run_tools(query: str):

    q = query.lower()

    # ---------------- CREDIT SCORE ----------------
    if "credit" in q:
        return {
            "type": "tool_response",
            "response": credit_score_analyzer.invoke({
                "credit_score": 720
            })
        }

    # ---------------- DTI ----------------
    if "dti" in q:
        return {
            "type": "tool_response",
            "response": dti_calculator.invoke({
                "income": 100000,
                "emi": 30000
            })
        }

    # ---------------- DOCUMENT ----------------
    if "document" in q or "pan" in q:
        return {
            "type": "tool_response",
            "response": document_verification.invoke({
                "document_type": "PAN",
                "document_number": "ABCDE1234F"
            })
        }

    # fallback
    return ask_llm(query)