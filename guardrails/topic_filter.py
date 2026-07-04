def is_banking_query(query: str) -> bool:
    q = query.lower()

    banking_keywords = [
        "credit", "loan", "emi", "dti", "bank", "account", "interest",
        "mortgage", "risk", "underwriting", "kyc", "pan", "aadhaar",
        "document", "verify", "verification", "cibil", "repayment",
        "collateral", "tenure", "sanction", "hi", "hello",
        "explain", "what", "how", "simple",
    ]

    return any(keyword in q for keyword in banking_keywords)