# FILE: tools/langchain_tools.py
"""LangChain @tool wrappers exposed to the agent (chains/tool_chain.py).
Each docstring is what the LLM sees when deciding whether to call a tool.

knowledge_retrieval deliberately does NOT expose `role`/`session_id` as
LLM-settable fields -- chains/tool_chain.py special-cases this tool and
calls the underlying tools.rag_tool.knowledge_retrieval() directly with
the authenticated caller's role injected server-side, so the model can
never widen its own document access by crafting a tool-call argument.
This tool's schema is kept here mainly so bind_tools() can advertise its
name/description/args to the LLM for tool selection.
"""
from typing import Optional

from langchain_core.tools import tool

from tools.credit_score_tool import credit_score_analyzer as _credit_score_analyzer
from tools.dti_tool import dti_calculator as _dti_calculator
from tools.document_tool import document_verification as _document_verification
from tools.advanced_tools import (
    max_loan_by_credit_score as _max_loan_by_credit_score,
    topup_eligibility as _topup_eligibility,
    max_allowed_emi as _max_allowed_emi,
    solve_tenure_for_emi as _solve_tenure_for_emi,
    simulate_rate_comparison as _simulate_rate_comparison,
)
from data.applicant_store import get_applicant, get_application


@tool
def get_applicant_record(identifier: str) -> dict:
    """Look up a stored applicant or loan-application record by ID
    (e.g. 'A-101' for an applicant ID, or '7745' for a loan-application
    number). Returns credit_score, monthly_income, emi, liabilities, pan,
    aadhaar, and risk_flags, or an error if no record matches."""
    record = get_applicant(identifier) or get_application(identifier)
    if not record:
        return {"error": f"No applicant or application record found for '{identifier}'."}
    return record


@tool
def credit_score_analyzer(credit_score: int) -> dict:
    """Classify credit risk and approval likelihood for a given credit score (300-900)."""
    return _credit_score_analyzer(credit_score)


@tool
def dti_calculator(monthly_income: float, emi: float) -> dict:
    """Calculate Debt-to-Income ratio and risk tier from monthly income and EMI
    (the monthly installment amount -- NOT total outstanding liabilities)."""
    return _dti_calculator(monthly_income=monthly_income, emi=emi)


@tool
def document_verification(pan: str, aadhaar: str) -> dict:
    """Verify PAN and Aadhaar number formats for KYC."""
    return _document_verification(pan=pan, aadhaar=aadhaar)


@tool
def max_loan_by_credit_score(credit_score: int) -> dict:
    """Indicative maximum loan amount based on credit score alone, assuming
    a benchmark income. Use only when the user hasn't given actual income;
    label the result indicative."""
    return _max_loan_by_credit_score(credit_score)


@tool
def topup_eligibility(monthly_income: float, existing_emi: float, requested_topup_emi: float = 0.0) -> dict:
    """Check whether adding a top-up EMI keeps the applicant's DTI within
    the safe 50% threshold."""
    return _topup_eligibility(monthly_income, existing_emi, requested_topup_emi)


@tool
def max_allowed_emi_for_target_dti(monthly_income: float, target_dti: float = 0.4) -> dict:
    """Return the maximum EMI that keeps DTI at or below a target ratio
    (default 40%) for the given monthly income."""
    return _max_allowed_emi(monthly_income, target_dti)


@tool
def solve_tenure_for_target_emi(principal: float, annual_rate_percent: float, target_emi: float) -> dict:
    """Solve for the minimum loan tenure in months so the EMI for this
    principal and annual interest rate does not exceed target_emi."""
    return _solve_tenure_for_emi(principal, annual_rate_percent, target_emi)


@tool
def simulate_rate_comparison(principal: float, tenure_months: int, rates: list[float]) -> dict:
    """Compare the monthly EMI for a given principal and tenure across
    multiple candidate annual interest rates."""
    return _simulate_rate_comparison(principal, tenure_months, rates)


@tool
def knowledge_retrieval(query: str, doc_type: Optional[str] = None, jurisdiction: Optional[str] = None, k: int = 5) -> dict:
    """Retrieve a grounded, cited answer from the indexed knowledge base:
    internal credit policy manual, RBI Master Circulars, the Fair Practices
    Code, and past anonymised underwriting memos. Use this for ANY question
    that depends on policy clause wording, regulatory references, or
    past-case precedent -- never answer these from general knowledge, and
    never invent a policy figure. Optionally filter by doc_type
    ('policy'|'circular'|'memo'|'audit') or jurisdiction; note the results
    are also always constrained by the requester's role permissions
    regardless of these hints. Returns {"response": <answer text with
    inline [chunk_id: ...] citations>, "citations": [...]}."""
    # NOTE: chains/tool_chain.py intercepts calls to this tool by name and
    # calls tools.rag_tool.knowledge_retrieval() directly instead of this
    # function, so that the authenticated role can be injected server-side.
    # This body only runs if knowledge_retrieval is invoked OUTSIDE the
    # agent loop (e.g. directly in a script/test) -- default to the most
    # restrictive role rather than silently granting broad access.
    from tools.rag_tool import knowledge_retrieval as _raw
    filters = {}
    if doc_type:
        filters["doc_type"] = doc_type
    if jurisdiction:
        filters["jurisdiction"] = jurisdiction
    return _raw(query, filters=filters or None, k=k, role="junior_analyst")