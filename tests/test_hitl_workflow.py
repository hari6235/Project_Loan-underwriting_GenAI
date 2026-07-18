# FILE: tests/test_hitl_workflow.py
"""Tests for HITL trigger evaluation, persistence, and the manager
workflow (Section 3.3, Week 8). All pure stdlib -- no mocking needed.

IMPORTANT: decision_context fixtures below use the REAL shape
chains/tool_chain.py actually produces -- {tool_name: tool_output_dict}
-- not made-up field names. An earlier version of this file (and of
config/hitl_rules.yaml) used field paths like bare "loan_amount" and
"credit_score_assessment.credit_score" that don't correspond to any real
tool name/output, so all 4 HITL rules were silently unreachable in
production while these tests still passed. test_all_rule_paths_resolve_to_real_tools
below guards against that exact class of bug recurring.
"""
import os
import tempfile

import pytest

from hitl.manager import HITLManager
from hitl.store import HITLStore
from hitl.triggers import TriggerEngine


@pytest.fixture
def engine():
    return TriggerEngine("config/hitl_rules.yaml")


@pytest.fixture
def manager():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield HITLManager(store=HITLStore(db_path=path), trigger_engine=TriggerEngine("config/hitl_rules.yaml"))
    os.remove(path)


# Realistic decision_context builders matching chains/tool_chain.py's
# actual assembly: {tool_name: tool_output}.
def _ctx_loan(amount, applicant_id="A-101"):
    return {"evaluate_loan_request": {"loan_amount": amount, "applicant_id": applicant_id, "size_tier": "large"}}


def _ctx_credit_score(score):
    return {"credit_score_analyzer": {"credit_score": score, "risk_level": "LOW" if score >= 650 else "REJECT"}}


def _ctx_dti(risk_level):
    return {"dti_calculator": {"dti_ratio": 0.6, "risk_level": risk_level, "max_loan_multiplier": 1.5}}


def _ctx_override(reason="user requested exception"):
    return {"flag_policy_override": {"flagged": True, "reason": reason}}


class TestTriggerEngine:
    def test_loads_all_four_rules(self, engine):
        assert {r.id for r in engine.rules} == {
            "high_loan_amount", "dti_policy_exception",
            "policy_override_requested", "low_credit_score",
        }

    def test_all_rule_paths_resolve_to_real_tools(self, engine):
        """Regression guard: every rule's field path must start with a
        real, currently-registered tool name (or a small allowlist of
        synthetic top-level keys), so a rule can never silently reference
        a tool/field that doesn't exist -- exactly the bug this file
        previously had on all 4 rules simultaneously."""
        from tools.tool_registry import TOOLS
        real_tool_names = {t.name for t in TOOLS}

        for rule in engine.rules:
            top_level_segment = rule.field.split(".")[0]
            assert top_level_segment in real_tool_names, (
                f"Rule '{rule.id}' references field '{rule.field}' whose top-level "
                f"segment '{top_level_segment}' is not a registered tool name. "
                f"Registered tools: {sorted(real_tool_names)}"
            )

    def test_high_loan_amount_triggers_above_50l(self, engine):
        matched = engine.evaluate(_ctx_loan(5_500_000))
        assert any(r.id == "high_loan_amount" for r in matched)

    def test_high_loan_amount_does_not_trigger_below_50l(self, engine):
        matched = engine.evaluate(_ctx_loan(3_000_000))
        assert not any(r.id == "high_loan_amount" for r in matched)

    def test_low_credit_score_triggers_below_650(self, engine):
        matched = engine.evaluate(_ctx_credit_score(610))
        assert any(r.id == "low_credit_score" for r in matched)

    def test_low_credit_score_does_not_trigger_at_or_above_650(self, engine):
        matched = engine.evaluate(_ctx_credit_score(650))
        assert not any(r.id == "low_credit_score" for r in matched)

    def test_dti_policy_exception_triggers_on_high_risk_level(self, engine):
        matched = engine.evaluate(_ctx_dti("HIGH"))
        assert any(r.id == "dti_policy_exception" for r in matched)

    def test_dti_policy_exception_does_not_trigger_on_low_risk_level(self, engine):
        matched = engine.evaluate(_ctx_dti("LOW"))
        assert not any(r.id == "dti_policy_exception" for r in matched)

    def test_policy_override_triggers_when_flagged(self, engine):
        matched = engine.evaluate(_ctx_override())
        assert any(r.id == "policy_override_requested" for r in matched)

    def test_policy_override_is_critical_severity(self, engine):
        matched = engine.evaluate(_ctx_override())
        assert engine.highest_severity(matched) == "critical"

    def test_no_rules_match_clean_context(self, engine):
        clean = {**_ctx_loan(100000), **_ctx_credit_score(800)}
        matched = engine.evaluate(clean)
        assert matched == []

    def test_multiple_rules_can_match_simultaneously(self, engine):
        combined = {**_ctx_loan(6_000_000), **_ctx_credit_score(600)}
        matched = engine.evaluate(combined)
        matched_ids = {r.id for r in matched}
        assert "high_loan_amount" in matched_ids
        assert "low_credit_score" in matched_ids

    def test_unknown_operator_raises(self, tmp_path):
        bad_rules = tmp_path / "bad_rules.yaml"
        bad_rules.write_text(
            "rules:\n  - id: bad\n    description: x\n    condition:\n      field: x\n"
            "      operator: not_a_real_operator\n      value: 1\n    severity: low\n"
        )
        bad_engine = TriggerEngine(str(bad_rules))
        with pytest.raises(ValueError):
            bad_engine.evaluate({"x": 1})


class TestHITLManagerWorkflow:
    def test_no_trigger_returns_none(self, manager):
        task = manager.check_and_create("sess-1", _ctx_loan(10000), "Approve")
        assert task is None

    def test_trigger_creates_pending_task(self, manager):
        task = manager.check_and_create("sess-2", _ctx_loan(6_000_000), "Recommend approval")
        assert task is not None
        assert task.status.value == "pending"
        assert manager.store.get(task.task_id).status.value == "pending"

    def test_pending_list_reflects_store(self, manager):
        manager.check_and_create("sess-3", _ctx_loan(6_000_000), "rec 1")
        manager.check_and_create("sess-4", _ctx_loan(7_000_000), "rec 2")
        assert len(manager.pending()) == 2

    def test_approve_resolves_task_and_removes_from_pending(self, manager):
        task = manager.check_and_create("sess-5", _ctx_loan(6_000_000), "rec")
        manager.review(task.task_id, decision="approve", decided_by="credit_head_1", comments="ok")
        assert manager.store.get(task.task_id).status.value == "approved"
        assert task.task_id not in [t.task_id for t in manager.pending()]

    def test_reject_resolves_task(self, manager):
        task = manager.check_and_create("sess-6", _ctx_loan(6_000_000), "rec")
        manager.review(task.task_id, decision="reject", decided_by="credit_head_1", comments="too risky")
        assert manager.store.get(task.task_id).status.value == "rejected"

    def test_double_review_raises(self, manager):
        task = manager.check_and_create("sess-7", _ctx_loan(6_000_000), "rec")
        manager.review(task.task_id, decision="approve", decided_by="a", comments=None)
        with pytest.raises(ValueError):
            manager.review(task.task_id, decision="approve", decided_by="b", comments=None)

    def test_review_unknown_task_raises(self, manager):
        with pytest.raises(KeyError):
            manager.review("nonexistent-id", decision="approve", decided_by="x", comments=None)

    def test_review_invalid_decision_raises(self, manager):
        task = manager.check_and_create("sess-8", _ctx_loan(6_000_000), "rec")
        with pytest.raises(ValueError):
            manager.review(task.task_id, decision="maybe", decided_by="x", comments=None)

    def test_task_persists_across_new_store_instance(self, manager):
        task = manager.check_and_create("sess-9", _ctx_loan(6_000_000), "rec")
        reopened_store = HITLStore(db_path=manager.store.db_path)
        assert reopened_store.get(task.task_id).status.value == "pending"