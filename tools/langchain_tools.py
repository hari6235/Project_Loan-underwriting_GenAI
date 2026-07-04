# FILE: tools/langchain_tools.py


from langchain_core.tools import tool

from tools.credit_score_tool import credit_score_analyzer as _credit_score_analyzer
from tools.dti_tool import dti_calculator as _dti_calculator
from tools.document_tool import document_verification as _document_verification


@tool
def credit_score_analyzer(credit_score: int) -> dict:
    """Classify credit risk and approval likelihood for a given credit score (300-900)."""
    return _credit_score_analyzer(credit_score)


@tool
def dti_calculator(monthly_income: float, emi: float) -> dict:
    """Calculate Debt-to-Income ratio and risk tier from monthly income and EMI."""
    return _dti_calculator(monthly_income=monthly_income, emi=emi)


@tool
def document_verification(pan: str, aadhaar: str) -> dict:
    """Verify PAN and Aadhaar number formats for KYC."""
    return _document_verification(pan=pan, aadhaar=aadhaar)