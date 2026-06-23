import re


def extract_credit_score(text: str):
    """
    Looks for patterns like:
      'credit score 720', 'score of 650', 'CIBIL 780', '720 score'
    Returns int or None.
    """
    patterns = [
        r'(?:credit\s*score|cibil|score\s*of|score)[^\d]*(\d{3})',
        r'(\d{3})\s*(?:credit\s*score|cibil|score)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 300 <= score <= 900:
                return score
    return None


def extract_income_and_emi(text: str):
    """
    Looks for patterns like:
      'income 50000', 'salary 1L', 'EMI 20000', 'emi of 15k'
    Returns (income, emi) tuple. Either can be None if not found.
    """
    def parse_amount(raw: str) -> float:
        raw = raw.replace(',', '').strip().lower()
        if raw.endswith('l'):
            return float(raw[:-1]) * 100000
        if raw.endswith('k'):
            return float(raw[:-1]) * 1000
        return float(raw)

    income = None
    emi = None

    income_match = re.search(
        r'(?:income|salary|earning)[^\d]*(\d[\d,]*(?:\.\d+)?[lkLK]?)',
        text, re.IGNORECASE
    )
    if income_match:
        try:
            income = parse_amount(income_match.group(1))
        except ValueError:
            pass

    emi_match = re.search(
        r'(?:emi|installment)[^\d]*(\d[\d,]*(?:\.\d+)?[lkLK]?)',
        text, re.IGNORECASE
    )
    if emi_match:
        try:
            emi = parse_amount(emi_match.group(1))
        except ValueError:
            pass

    return income, emi


def extract_pan(text: str):
    """Extracts PAN card number like ABCDE1234F."""
    match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)
    return match.group(1) if match else None


def extract_aadhaar(text: str):
    """Extracts 12-digit Aadhaar number."""
    match = re.search(r'\b(\d{12})\b', text)
    return match.group(1) if match else None