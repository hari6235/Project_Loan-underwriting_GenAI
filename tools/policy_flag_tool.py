# FILE: tools/policy_flag_tool.py
"""Gives the agent's own judgment about an override request a place to
land as structured data. The agent decides (via the system prompt, see
prompts/agent_system.yaml) WHEN the user is asking to bypass/override
stated policy -- this tool doesn't do that judgment itself, it just
records it so hitl/triggers.py's dotted-path lookup has something real
to check (previously, chains/hitl_chain.py checked
payload["policy_override_requested"], but nothing ever set that key)."""


def flag_policy_override(reason: str) -> dict:
    return {"flagged": True, "reason": reason or "No reason given"}