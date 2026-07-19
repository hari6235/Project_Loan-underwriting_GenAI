def is_banking_query(query: str) -> bool:
    """Fast, permissive client-side pre-filter meant only to catch
    OBVIOUSLY off-topic messages (weather, jokes, general chit-chat)
    before spending an LLM call on them. This is deliberately broad --
    the agent's own system prompt (prompts/agent_system.yaml) already has
    smarter, context-aware topic guidance as a second layer, so a false
    POSITIVE here just costs one wasted LLM call (which will then
    politely decline), while a false NEGATIVE blocks a legitimate query
    outright with no fallback. Err toward permissive."""
    q = query.lower()

    banking_keywords = [
        "credit", "loan", "emi", "dti", "bank", "account", "interest",
        "mortgage", "risk", "underwriting", "kyc", "pan", "aadhaar",
        "document", "verify", "verification", "cibil", "repayment",
        "collateral", "tenure", "sanction", "hi", "hello",
        "explain", "what", "how", "simple",
        # Applicant/application data -- get_applicant_record's whole domain
        "applicant", "application", "record", "borrower", "customer",
        "profile", "score", "id ", "id-", "id#", "#",
        # Policy/regulatory -- knowledge_retrieval's whole domain
        "policy", "regulatory", "regulation", "circular", "rbi", "clause",
        "fair practices", "compliance", "audit", "memo", "override",
        "exception", "waive", "bypass",
        # Loan mechanics -- advanced_tools.py's whole domain
        "topup", "top-up", "top up", "ltv", "eligib", "approv", "reject",
        "recommend", "principal", "income", "salary", "rate", "valuation",
        "property", "disburs", "restructur", "npa",
    ]

    return any(keyword in q for keyword in banking_keywords)