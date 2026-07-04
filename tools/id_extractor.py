import re


def extract_applicant_id(text: str):
    """Matches patterns like 'A-9912', 'A-101'. Returns None if not found."""
    match = re.search(r'\bA-\d+\b', text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def extract_all_applicant_ids(text: str):
    """Returns every applicant ID found (used for compare-style queries)."""
    return [m.upper() for m in re.findall(r'\bA-\d+\b', text, re.IGNORECASE)]


def extract_application_id(text: str):
    """Matches patterns like '#7745', 'application 7745', 'application #7745'."""
    match = re.search(r'#\s*(\d{3,6})\b', text)
    if match:
        return match.group(1)
    match = re.search(r'application\s*(?:id)?\s*(?:number)?\s*[:#]?\s*(\d{3,6})\b', text, re.IGNORECASE)
    return match.group(1) if match else None