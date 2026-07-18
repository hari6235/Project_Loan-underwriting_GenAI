# FILE: tools/loan_request_tool.py
"""Captures the loan amount actually being recommended/approved as
structured data. Without this, "loan_amount" never exists anywhere in
decision_context (see config/hitl_rules.yaml's high_loan_amount rule) --
no other tool takes a requested loan amount as input/output, so the
HITL gate could never see it no matter what the agent said in prose."""


def evaluate_loan_request(loan_amount: float, applicant_id: str = None) -> dict:
    if loan_amount is None or loan_amount <= 0:
        return {"error": "loan_amount must be a positive number"}

    if loan_amount > 10_000_000:
        size_tier = "very_large"
    elif loan_amount > 5_000_000:
        size_tier = "large"
    elif loan_amount > 1_000_000:
        size_tier = "medium"
    else:
        size_tier = "small"

    return {
        "loan_amount": float(loan_amount),
        "applicant_id": applicant_id,
        "size_tier": size_tier,
    }