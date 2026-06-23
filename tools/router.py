# FILE: tools/router.py

from tools.credit_score_tool import credit_score_analyzer
from tools.dti_tool import dti_calculator
from tools.document_tool import document_verification
from tools.parse_values import (
    extract_credit_score,
    extract_income_and_emi,
    extract_pan,
    extract_aadhaar,
)

# Fallback defaults — used only when user provides no numbers
DEFAULT_CREDIT_SCORE = 700
DEFAULT_INCOME = 50000
DEFAULT_EMI = 15000


def tool_router(query: str):

    query_lower = query.lower()

    # -------------------- CREDIT SCORE --------------------
    if "credit score" in query_lower or "cibil" in query_lower:
        score = extract_credit_score(query) or DEFAULT_CREDIT_SCORE
        return credit_score_analyzer(score)

    # -------------------- DTI / EMI --------------------
    if "dti" in query_lower or "emi" in query_lower or "debt" in query_lower:
        income, emi = extract_income_and_emi(query)
        income = income or DEFAULT_INCOME
        emi = emi or DEFAULT_EMI
        return dti_calculator(
            monthly_income=income,
            emi=emi,
        )

    # -------------------- KYC / DOCUMENT --------------------
    if "kyc" in query_lower or "pan" in query_lower or "aadhaar" in query_lower:
        pan = extract_pan(query) or "NOT_PROVIDED"
        aadhaar = extract_aadhaar(query) or "NOT_PROVIDED"
        return document_verification(pan=pan, aadhaar=aadhaar)

    return None