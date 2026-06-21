from langchain_core.tools import tool

# -------------------------
# CREDIT SCORE TOOL
# -------------------------
@tool
def credit_score_analyzer(applicant_id: str) -> dict:
    """
    Fetch credit score and classify risk.
    """

    # Dummy logic (replace with your existing logic later)
    credit_score = 720

    if credit_score >= 750:
        category = "EXCELLENT"
        risk = "LOW"
        approval = "95%"
    elif credit_score >= 700:
        category = "GOOD"
        risk = "MEDIUM"
        approval = "80%"
    else:
        category = "POOR"
        risk = "HIGH"
        approval = "40%"

    return {
        "applicant_id": applicant_id,
        "credit_score": credit_score,
        "category": category,
        "risk_level": risk,
        "approval_probability": approval
    }


# -------------------------
# DTI CALCULATOR TOOL
# -------------------------
@tool
def dti_calculator(income: float, emi: float) -> dict:
    """
    Calculate Debt-to-Income ratio.
    """

    dti = emi / income

    if dti <= 0.3:
        status = "LOW RISK"
    elif dti <= 0.5:
        status = "MEDIUM RISK"
    else:
        status = "HIGH RISK"

    return {
        "income": income,
        "emi": emi,
        "dti": round(dti, 2),
        "status": status
    }


# -------------------------
# DOCUMENT VERIFICATION TOOL
# -------------------------
@tool
def document_verification(document_type: str, document_number: str) -> dict:
    """
    Validate KYC / loan documents.
    """

    valid_docs = ["PAN", "AADHAAR", "ITR"]

    if document_type.upper() in valid_docs:
        status = "VALID"
    else:
        status = "INVALID"

    return {
        "document_type": document_type,
        "document_number": document_number,
        "verification_status": status
    }