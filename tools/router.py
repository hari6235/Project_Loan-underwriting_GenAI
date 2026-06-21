from tools.credit_score_tool import credit_score_analyzer
from tools.dti_tool import dti_calculator
from tools.document_tool import document_verification


def tool_router(query: str):

    query_lower = query.lower()

    if "credit score" in query_lower:
        return credit_score_analyzer(720)

    if "dti" in query_lower or "emi" in query_lower:
        return dti_calculator(
            monthly_income=100000,
            emi=30000
        )

    if "kyc" in query_lower or "pan" in query_lower:
        return document_verification(
            pan="ABCDE1234F",
            aadhaar="123456789012"
        )

    return None