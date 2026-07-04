import math


def max_loan_by_credit_score(credit_score: int) -> dict:
    """
    Indicative maximum loan amount based on credit score ALONE, assuming a
    benchmark income. This is clearly labeled as indicative because a real
    max-loan figure also depends on the applicant's actual income and DTI.
    """
    if credit_score >= 750:
        multiplier, band = 6, "EXCELLENT"
    elif credit_score >= 700:
        multiplier, band = 5, "GOOD"
    elif credit_score >= 650:
        multiplier, band = 3, "MODERATE"
    else:
        multiplier, band = 1, "HIGH_RISK"

    benchmark_monthly_income = 50000
    indicative_max_loan = multiplier * benchmark_monthly_income * 12

    return {
        "credit_score": credit_score,
        "band": band,
        "indicative_max_loan_multiplier": multiplier,
        "indicative_max_loan_amount": indicative_max_loan,
        "note": (
            "Indicative estimate based on credit score alone, assuming a "
            f"benchmark monthly income of ₹{benchmark_monthly_income:,}. "
            "Actual eligibility depends on the applicant's real income, EMI, and DTI ratio."
        ),
    }


def topup_eligibility(monthly_income: float, existing_emi: float, requested_topup_emi: float = 0.0) -> dict:
    """Checks whether adding a top-up EMI keeps DTI within a safe (50%) threshold."""
    if not monthly_income:
        return {"error": "Monthly income is required to assess top-up eligibility."}

    current_dti = existing_emi / monthly_income
    projected_emi = existing_emi + requested_topup_emi
    projected_dti = projected_emi / monthly_income
    eligible = projected_dti <= 0.5

    return {
        "current_dti": round(current_dti, 2),
        "projected_dti_with_topup": round(projected_dti, 2),
        "eligible": eligible,
        "recommendation": (
            "Eligible for top-up within safe DTI limits (<=50%)."
            if eligible else
            "Not eligible at this top-up amount — projected DTI exceeds the 50% safe threshold. "
            "Consider a smaller top-up amount or a longer tenure."
        ),
    }


def max_allowed_emi(monthly_income: float, target_dti: float = 0.4) -> dict:
    """Returns the maximum EMI that keeps DTI at or below the target ratio."""
    return {
        "monthly_income": monthly_income,
        "target_dti": target_dti,
        "max_allowed_emi": round(monthly_income * target_dti, 2),
    }


def compute_emi(principal: float, annual_rate_percent: float, tenure_months: int) -> float:
    """Standard reducing-balance EMI formula."""
    r = (annual_rate_percent / 12) / 100
    if r == 0:
        return principal / tenure_months
    factor = (1 + r) ** tenure_months
    return principal * r * factor / (factor - 1)


def solve_tenure_for_emi(principal: float, annual_rate_percent: float, target_emi: float) -> dict:
    """
    Solves for the minimum tenure (in months) so the EMI for this principal
    and rate does not exceed target_emi.
    """
    r = (annual_rate_percent / 12) / 100

    if r == 0:
        n = math.ceil(principal / target_emi)
        return {"tenure_months": n, "monthly_rate": r}

    denom = target_emi - principal * r
    if denom <= 0:
        return {"error": "Target EMI is too low to ever repay this principal at this interest rate."}

    n = math.log(target_emi / denom) / math.log(1 + r)
    return {"tenure_months": math.ceil(n), "monthly_rate": round(r, 5)}


def simulate_rate_comparison(principal: float, tenure_months: int, rates: list) -> dict:
    """Compares EMI across multiple candidate interest rates."""
    comparison = [
        {"interest_rate": rate, "emi": round(compute_emi(principal, rate, tenure_months), 2)}
        for rate in rates
    ]
    return {
        "principal": principal,
        "tenure_months": tenure_months,
        "comparison": comparison,
    }