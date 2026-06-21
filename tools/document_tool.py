import re

def document_verification(pan: str, aadhaar: str) -> dict:

    pan_valid = bool(re.match(r"[A-Z]{5}[0-9]{4}[A-Z]", pan))
    aadhaar_valid = bool(re.match(r"\d{12}", aadhaar))

    if pan_valid and aadhaar_valid:
        status = "VERIFIED"
        risk_flag = "NONE"
    else:
        status = "FAILED"
        risk_flag = "HIGH"

    return {
        "pan_valid": pan_valid,
        "aadhaar_valid": aadhaar_valid,
        "status": status,
        "risk_flag": risk_flag
    }