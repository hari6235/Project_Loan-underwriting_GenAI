"""
Applicant/application data store.

"""

from typing import Optional


_APPLICANTS = {
    "A-9912": {
        "applicant_id": "A-9912",
        "credit_score": 640,
        "monthly_income": 100000,
        "emi": 42000,
        "liabilities": 480000,
        "pan": "ABCDE1234F",
        "aadhaar": "123456789012",
        "risk_flags": [
            "High DTI ratio (42%)",
            "Credit score below 650 threshold",
            "Income volatility in last 6 months",
        ],
    },
    "A-101": {
        "applicant_id": "A-101",
        "credit_score": 760,
        "monthly_income": 150000,
        "emi": 30000,
        "liabilities": 300000,
        "pan": "PQRSX5678K",
        "aadhaar": "987654321098",
        "risk_flags": [],
    },
    "A-102": {
        "applicant_id": "A-102",
        "credit_score": 690,
        "monthly_income": 90000,
        "emi": 40000,
        "liabilities": 500000,
        "pan": "LMNOQ4321Z",
        "aadhaar": "234567890123",
        "risk_flags": [
            "Moderate credit score band (690)",
            "DTI ratio at 44% — within medium-risk range",
            "Liabilities represent a significant share of income",
        ],
    },
}

# Loan application IDs map to an underlying applicant record.
_APPLICATIONS = {
    "7745": {"application_id": "7745", "applicant_id": "A-101"},
    "3310": {"application_id": "3310", "applicant_id": "A-9912"},
    "8899": {"application_id": "8899", "applicant_id": "A-102"},
    "5521": {"application_id": "5521", "applicant_id": "A-101"},
}


def get_applicant(applicant_id: str) -> Optional[dict]:
    return _APPLICANTS.get(applicant_id.upper())


def get_application(application_id: str) -> Optional[dict]:
    app = _APPLICATIONS.get(application_id)
    if not app:
        return None
    applicant = get_applicant(app["applicant_id"])
    if not applicant:
        return None
    merged = dict(applicant)
    merged["application_id"] = application_id
    return merged