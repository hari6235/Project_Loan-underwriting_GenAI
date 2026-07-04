# FILE: services/llm_service.py

import os
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.logger import get_logger

load_dotenv()

logger = get_logger("services.llm_service")

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

_llm_singleton: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
    """Process-wide singleton so every caller shares one client instead of
    re-instantiating (and re-authenticating) per call."""
    global _llm_singleton
    if _llm_singleton is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set.")
        _llm_singleton = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=api_key)
        logger.info("LLM client initialised: model=%s temperature=%.2f", LLM_MODEL, LLM_TEMPERATURE)
    return _llm_singleton


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def ask_llm(query: str) -> dict:
    """Direct LLM call with retry on transient failures. Used for simple,
    single-turn calls; core/chain.py uses get_llm() directly when it needs
    a full ChatPromptTemplate with history."""
    llm = get_llm()
    try:
        response = llm.invoke(query)
    except Exception:
        logger.exception("LLM invocation failed for a query of length %d", len(query))
        raise

    return {
        "type": "llm_response",
        "response": response.content,
    }