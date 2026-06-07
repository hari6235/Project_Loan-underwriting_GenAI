BANKING_KEYWORDS = [
    "loan",
    "credit",
    "bank",
    "account",
    "kyc",
    "interest",
    "insurance",
    "emi",
    "mortgage"
]


def is_banking_query(text: str) -> bool:
    text = text.lower()

    return any(
        keyword in text
        for keyword in BANKING_KEYWORDS
    )