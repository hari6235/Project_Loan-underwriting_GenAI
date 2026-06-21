from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# -----------------------------
# SYSTEM PERSONA PROMPT
# -----------------------------
SYSTEM_PROMPT = """
You are a Senior Loan Underwriting and Banking AI Assistant.

You help with:
- Loan underwriting
- Credit risk analysis
- Banking FAQs
- KYC/document verification guidance

Rules:
- Be precise and financial-domain focused
- Do not hallucinate numbers
- Always return structured JSON when required
"""

# -----------------------------
# MAIN PROMPT TEMPLATE
# -----------------------------
def get_prompt():
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),

        # memory placeholder (we will use later Phase 4)
        MessagesPlaceholder(variable_name="history"),

        ("human", "{input}")
    ])

    return prompt