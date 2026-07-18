import re


def contains_pii(text: str) -> bool:
    """Blocks PII patterns that should NEVER be typed into this chat under
    any legitimate workflow.

    PAN and Aadhaar are deliberately NOT on this list: document_verification
    (tools/document_tool.py) is a core banking tool whose entire job is to
    accept and validate a PAN + Aadhaar pair for KYC. Blocking those exact
    patterns made that feature permanently unusable through the chat UI --
    a self-defeating guardrail, not a safety win. Handling of PAN/Aadhaar is
    now covered by role-based access control and audit logging
    (rbac/audit.py logs every retrieval; extend similarly if you want a
    dedicated audit trail for KYC submissions specifically).

    Card numbers and CVVs, by contrast, are never a legitimate input to any
    tool in this app and are blocked outright.
    """
    patterns = [
        r"\b\d{10}\b",                                   # phone number -- no tool needs this as input
        r"\b(?:\d[ -]*?){13,16}\b",                      # credit/debit card number (13-16 digits, optionally spaced/dashed)
        r"\bcvv\s*:?\s*\d{3,4}\b",                       # CVV, explicitly labeled
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False