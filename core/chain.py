# FILE: core/chain.py

import json

from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential

from services.llm_service import get_llm
from tools.router import tool_router
from vectorstore.example_store import search_examples
from utils.logger import get_logger

logger = get_logger("core.chain")

SYSTEM_PROMPT = (
    "You are a Senior Loan Underwriting and Credit Risk Assistant for a bank. "
    "Begin with a greeting and answer clearly and simply. If the user asks something outside banking, "
    "loans, or credit risk, politely say you can only help with those topics.\n\n"
    "IMPORTANT — data honesty rules:\n"
    "1. You do NOT have access to a live applicant database, uploaded documents, or historical "
    "default-rate datasets beyond what already appears in this conversation's tool results and history.\n"
    "2. NEVER invent specific numbers, applicant records, document contents, or default rates that "
    "were not explicitly provided in the conversation history or a tool result shown above.\n"
    "3. If asked about a specific applicant/application ID and no matching data appears in this "
    "conversation, say plainly that you don't have that record and ask the user to provide the details "
    "directly (credit score, income, EMI, PAN/Aadhaar, etc.).\n"
    "4. For general banking/regulatory/conceptual questions (e.g. regulatory guidelines, how a guarantor "
    "affects risk, what documents are typically required, collateral options to reduce risk tier), you may "
    "answer using general, well-established banking knowledge — but label it clearly as general guidance, "
    "not a verified match to this bank's specific policy, and suggest the user confirm with the compliance "
    "or credit team.\n"
    "5. When asked to summarize or generate a memo, base it ONLY on the tool results and messages already "
    "present in the conversation history — do not add figures that weren't stated.\n"
    "6. If asked to review uploaded documents (e.g. bank statements) and none have actually been provided "
    "in this conversation, say you don't currently have the document content and ask the user to paste "
    "the relevant figures or confirm how the document was shared."
)


def _format_history(history: list) -> str:
    """`history` comes from MemoryStore.get(): a list of
    {"user": ..., "assistant": ...} dicts, where "assistant" is a JSON string
    (see api/routes.py's memory.add call). Unwrap it back to plain text
    instead of feeding raw JSON into the prompt."""
    lines = []
    for turn in history:
        user_msg = turn.get("user", "")
        assistant_raw = turn.get("assistant", "")
        try:
            parsed = json.loads(assistant_raw)
            assistant_msg = parsed.get("response", assistant_raw) if isinstance(parsed, dict) else assistant_raw
        except (json.JSONDecodeError, TypeError):
            assistant_msg = assistant_raw
        lines.append(f"User: {user_msg}\nAssistant: {assistant_msg}")
    return "\n".join(lines)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def _invoke_llm(messages):
    return get_llm().invoke(messages)


def run_chain(user_input: str, history: list) -> dict:
    """
    Single decision point for every /chat request:
      1. Try the deterministic tool router (credit score / DTI / KYC / RAG / etc.),
         passing conversation history so follow-up queries that reference
         "this applicant" without repeating an ID can still resolve.
      2. If no tool matches, fall back to the LLM with conversation history
         and a retrieved few-shot example.

    Returns {"type": ..., "response": ...} — the same shape api/routes.py
    already persists to memory and returns to the client. When the RAG tool
    fires, the return dict also carries a top-level "citations" list.
    """
    user_input = user_input.strip()
    if not user_input:
        return {"type": "clarification", "response": "Please enter a question."}

    # 1. TOOL FIRST (history passed in for follow-up / context resolution)
    tool_result = tool_router(user_input, history)
    if tool_result is not None:
        logger.info("Routed to tool | input_preview=%.80s", user_input)

        # RAG responses carry their own type + citations one level down
        # (see tools/rag_tool.py). Unwrap them to the top level here so
        # api/routes.py can read result["type"] == "rag_response" and
        # result["citations"] directly, instead of them being buried inside
        # the generic {"type": "tool_response", "response": ...} envelope
        # that every other (non-RAG) tool result still uses unchanged.
        if isinstance(tool_result, dict) and tool_result.get("type") == "rag_response":
            return {
                "type": "rag_response",
                "response": tool_result.get("response"),
                "citations": tool_result.get("citations", []),
            }

        return {"type": "tool_response", "response": tool_result}

    # 2. LLM FALLBACK (few-shot + history)
    logger.info("Routed to LLM | input_preview=%.80s", user_input)
    example = search_examples(user_input)
    history_text = _format_history(history)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", "Conversation history:\n{history}"),
            ("user", "Relevant example:\n{example}"),
            ("user", "{input}"),
        ]
    )
    messages = prompt.format_messages(
        input=user_input,
        history=history_text if history_text else "(none)",
        example=str(example) if example else "(none)",
    )

    try:
        response = _invoke_llm(messages)
    except Exception:
        logger.exception("LLM invocation failed after retries.")
        return {
            "type": "error",
            "response": "The assistant is temporarily unavailable. Please try again shortly.",
        }

    try:
        parsed_response = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        parsed_response = response.content

    return {"type": "llm_response", "response": parsed_response}