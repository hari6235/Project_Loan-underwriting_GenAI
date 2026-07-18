# FILE: hitl/triggers.py
"""Evaluates config/hitl_rules.yaml rules against a decision_context dict
assembled by the agent for the current turn (tool outputs, extracted
figures, explicit override requests, etc). Pure logic, no I/O beyond
loading the YAML, so it's directly unit-testable."""
from __future__ import annotations

from dataclasses import dataclass

import yaml

DEFAULT_RULES_PATH = "config/hitl_rules.yaml"

_OPERATORS = {
    "gt": lambda a, b: a is not None and a > b,
    "gte": lambda a, b: a is not None and a >= b,
    "lt": lambda a, b: a is not None and a < b,
    "lte": lambda a, b: a is not None and a <= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "in": lambda a, b: a in b if b is not None else False,
    "contains": lambda a, b: (b is not None and a is not None and b in a),
    "exists": lambda a, b: a is not None,
}

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class TriggerRule:
    id: str
    description: str
    field: str
    operator: str
    value: object
    severity: str


def _dotted_get(d: dict, path: str):
    node = d
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


class TriggerEngine:
    def __init__(self, rules_path: str = DEFAULT_RULES_PATH):
        self.rules_path = rules_path
        self.rules: list[TriggerRule] = []
        self.default_expiry_hours: int = 48
        self.reload()

    def reload(self) -> None:
        with open(self.rules_path, "r") as f:
            raw = yaml.safe_load(f) or {}
        self.default_expiry_hours = int(raw.get("default_expiry_hours", 48))
        self.rules = [
            TriggerRule(
                id=r["id"],
                description=r.get("description", ""),
                field=r["condition"]["field"],
                operator=r["condition"]["operator"],
                value=r["condition"].get("value"),
                severity=r.get("severity", "medium"),
            )
            for r in raw.get("rules", [])
        ]

    def evaluate(self, decision_context: dict) -> list[TriggerRule]:
        """Returns every rule whose condition matches decision_context.
        Unknown operators raise loudly rather than silently passing --
        a misconfigured rule should never fail open."""
        matched = []
        for rule in self.rules:
            op_fn = _OPERATORS.get(rule.operator)
            if op_fn is None:
                raise ValueError(f"Unknown HITL operator '{rule.operator}' in rule '{rule.id}'")
            actual = _dotted_get(decision_context, rule.field)
            if op_fn(actual, rule.value):
                matched.append(rule)
        return matched

    @staticmethod
    def highest_severity(rules: list[TriggerRule]) -> str | None:
        if not rules:
            return None
        return max(rules, key=lambda r: _SEVERITY_RANK.get(r.severity, 0)).severity