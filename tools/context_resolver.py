from tools.id_extractor import extract_applicant_id, extract_application_id
from data.applicant_store import get_applicant, get_application


def resolve_applicant(query: str, history: list = None):
    """
    Resolves an applicant record referenced in the current query.
    If the current query doesn't name an ID directly (e.g. a follow-up like
    'Re-run underwriting after salary revision'), falls back to the most
    recently mentioned applicant/application ID in the conversation history.
    Returns a dict or None.
    """
    applicant_id = extract_applicant_id(query)
    if applicant_id:
        record = get_applicant(applicant_id)
        if record:
            return record

    application_id = extract_application_id(query)
    if application_id:
        record = get_application(application_id)
        if record:
            return record

    if history:
        for turn in reversed(history):
            combined = f"{turn.get('user', '')} {turn.get('assistant', '')}"

            aid = extract_applicant_id(combined)
            if aid:
                record = get_applicant(aid)
                if record:
                    return record

            appid = extract_application_id(combined)
            if appid:
                record = get_application(appid)
                if record:
                    return record

    return None