import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

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
# TOOL ROUTER — delegates to tools/router.py (single source of truth)
# -------------------------
def run_tools(query: str):

    from tools.router import tool_router

    result = tool_router(query)

    if result:
        return {
            "type": "tool_response",
            "response": result
        }

    # fallback to LLM if no tool matched
    return ask_llm(query)