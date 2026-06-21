def credit_score_analyzer(credit_score: int) -> dict:

    if credit_score >= 750:
        category = "EXCELLENT"
        risk = "LOW"
        approval = 95

    elif 700 <= credit_score < 750:
        category = "GOOD"
        risk = "MEDIUM"
        approval = 80

    elif 650 <= credit_score < 700:
        category = "MODERATE"
        risk = "HIGH"
        approval = 60

    else:
        category = "POOR"
        risk = "REJECT"
        approval = 20

    return {
        "credit_score": int(credit_score),
        "category": category,
        "risk_level": risk,
        "approval_probability": approval
    }