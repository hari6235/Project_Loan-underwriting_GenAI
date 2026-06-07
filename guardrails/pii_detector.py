import re


def contains_pii(text: str) -> bool:

    patterns = [
        r"\b\d{12}\b",               # Aadhaar
        r"[A-Z]{5}[0-9]{4}[A-Z]",    # PAN
        r"\b\d{10}\b"                # Phone
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False