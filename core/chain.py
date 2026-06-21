import os
import json

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from vectorstore.example_store import search_examples
from tools.router import tool_router
load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY")
)


def safe_parse(response_text: str):

    try:
        return json.loads(response_text)
    except:

        return {
            "category": "fallback",
            "answer": response_text,
            "confidence_score": 0.5,
            "recommendation": "Generated fallback response"
        }


def run_chain(user_input: str, memory: list):

    # 1. TOOL FIRST (IMPORTANT)
    tool_result = tool_router(user_input)

    if tool_result:
        return {
            "type": "tool_response",
            "response": tool_result
        }

    # 2. FALLBACK TO LLM
    example = search_examples(user_input)

    history_text = "\n".join(
        [f"{m['role']}: {m['message']}" for m in memory]
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a Senior Loan Underwriting Assistant. Return JSON only."),
        ("user", f"History:\n{history_text}"),
        ("user", f"Examples:\n{example}"),
        ("user", "{input}")
    ])

    messages = prompt.format_messages(input=user_input)

    response = llm.invoke(messages)

    try:
        return {
            "type": "llm_response",
            "response": json.loads(response.content)
        }
    except:
        return {
            "type": "llm_response",
            "response": response.content
        }