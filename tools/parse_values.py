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


def _parse_amount(raw: str) -> float:
    raw = raw.replace(',', '').strip().lower()
    if raw.endswith('l'):
        return float(raw[:-1]) * 100000
    if raw.endswith('k'):
        return float(raw[:-1]) * 1000
    return float(raw)


def extract_income_and_emi(text: str):
    """
    Looks for patterns like:
      'income 50000', 'salary 1L', 'EMI 20000', 'emi of 15k',
      'annual income 12L', 'income 12L per annum', 'salary revision to 15L'

    Income is normalized to MONTHLY before being returned, since
    dti_calculator expects monthly_income.

    Default convention (matches common Indian usage):
      - Explicit 'monthly' / 'per month' -> treated as monthly, no conversion.
      - Explicit 'annual' / 'per annum' / 'yearly' / 'ctc' -> divided by 12.
      - No explicit qualifier, but unit is Lakhs ('L') -> assumed ANNUAL
        (salary quoted in Lakhs is conventionally an annual/CTC figure),
        divided by 12.
      - No explicit qualifier, plain number or 'K' unit -> assumed already
        MONTHLY, no conversion.

    Returns (monthly_income, emi) tuple. Either can be None if not found.
    """
    text_lower = text.lower()
    is_annual_explicit = bool(re.search(
        r'annual|per annum|p\.?a\.?|yearly|/\s*year|per year|ctc', text_lower
    ))
    is_monthly_explicit = bool(re.search(
        r'per month|/\s*month|monthly', text_lower
    ))

    income = None
    emi = None

    income_match = re.search(
        r'(?:income|salary|earning)[^\d]*(\d[\d,]*(?:\.\d+)?[lkLK]?)',
        text, re.IGNORECASE
    )
    if income_match:
        raw = income_match.group(1)
        try:
            income = _parse_amount(raw)
            unit_is_lakh = raw.strip().lower().endswith('l')

            if is_monthly_explicit:
                pass  # already monthly
            elif is_annual_explicit:
                income = income / 12
            elif unit_is_lakh:
                income = income / 12  # default: Lakh figures are annual
            # else: plain number or 'k' unit -> assume already monthly
        except ValueError:
            income = None

    emi_match = re.search(
        r'(?:emi|installment)[^\d]*(\d[\d,]*(?:\.\d+)?[lkLK]?)',
        text, re.IGNORECASE
    )
    if emi_match:
        try:
            emi = _parse_amount(emi_match.group(1))
        except ValueError:
            pass

    return income, emi


def extract_liabilities(text: str):
    """
    Detects a total-liabilities / outstanding-debt figure, distinct from
    EMI (a monthly installment) and not a valid substitute for it in DTI
    calculation. Returns float or None.
    """
    match = re.search(
        r'(?:liabilit(?:y|ies)|outstanding\s*debt|total\s*debt)[^\d]*(\d[\d,]*(?:\.\d+)?[lkLK]?)',
        text, re.IGNORECASE
    )
    if not match:
        return None
    try:
        return _parse_amount(match.group(1))
    except ValueError:
        return None


def extract_principal(text: str):
    """Detects a loan principal amount, e.g. 'principal 25L', 'loan amount 10L'."""
    match = re.search(
        r'(?:principal|loan amount|loan of)[^\d]*(\d[\d,]*(?:\.\d+)?[lkLK]?)',
        text, re.IGNORECASE
    )
    if not match:
        return None
    try:
        return _parse_amount(match.group(1))
    except ValueError:
        return None


def extract_tenure_months(text: str):
    """Detects tenure in months or years (converted to months)."""
    match = re.search(r'(\d+)\s*(?:month|months)\b', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)\s*(?:year|years|yr|yrs)\b', text, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 12
    return None


def extract_all_rates(text: str):
    """Returns every percentage figure found, e.g. '9.5% vs 10.5%' -> [9.5, 10.5]."""
    return [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*%', text)]


def extract_first_rate(text: str):
    rates = extract_all_rates(text)
    return rates[0] if rates else None


def extract_pan(text: str):
    """Extracts PAN card number like ABCDE1234F."""
    match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)
    return match.group(1) if match else None


def extract_aadhaar(text: str):
    """Extracts 12-digit Aadhaar number."""
    match = re.search(r'\b(\d{12})\b', text)
    return match.group(1) if match else None