def dti_calculator(monthly_income: float, emi: float) -> dict:

    if monthly_income == 0:
        return {
            "error": "Income cannot be zero"
        }

    dti = emi / monthly_income

    if dti <= 0.3:
        risk_level = "LOW"
        max_loan_multiplier = 5

    elif dti <= 0.5:
        risk_level = "MEDIUM"
        max_loan_multiplier = 3

    else:
        risk_level = "HIGH"
        max_loan_multiplier = 1.5

    return {
        "dti_ratio": round(dti, 2),
        "risk_level": risk_level,
        "max_loan_multiplier": max_loan_multiplier
    }