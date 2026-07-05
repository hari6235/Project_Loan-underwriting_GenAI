# FILE: services/llm_service.py
import os
from typing import Optional

from utils.langsmith_config import configure_langsmith

configure_langsmith()

from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.logger import get_logger

logger = get_logger("services.llm_service")

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Keyed by temperature so each distinct temperature gets its own reusable
# singleton, instead of re-instantiating per call. Default (no arg) behaves
# exactly as before: one shared client at LLM_TEMPERATURE.
_llm_clients: dict[float, ChatOpenAI] = {}


def get_llm(temperature: Optional[float] = None) -> ChatOpenAI:
    """Process-wide singleton (per temperature) so every caller shares one
    client instead of re-instantiating (and re-authenticating) per call.
    Pass temperature=0 for grounded/citation-sensitive generation (e.g. RAG);
    omit it for the existing default behavior."""
    global _llm_clients
    temp = temperature if temperature is not None else LLM_TEMPERATURE
    if temp not in _llm_clients:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set.")
        _llm_clients[temp] = ChatOpenAI(model=LLM_MODEL, temperature=temp, api_key=api_key)
        logger.info("LLM client initialised: model=%s temperature=%.2f", LLM_MODEL, temp)
    return _llm_clients[temp]


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