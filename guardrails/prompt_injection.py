def detect_prompt_injection(text: str) -> bool:

    attacks = [
        "ignore previous instructions",
        "reveal system prompt",
        "act as",
        "bypass",
        "developer message"
    ]

    text = text.lower()

    return any(
        attack in text
        for attack in attacks
    )