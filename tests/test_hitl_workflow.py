# FILE: tests/test_hitl_workflow.py
"""Tests for HITL trigger evaluation, persistence, and the manager
workflow (Section 3.3, Week 8). All pure stdlib -- no mocking needed."""
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


class TestTriggerEngine:
    def test_loads_all_four_rules(self, engine):
        assert {r.id for r in engine.rules} == {
            "high_loan_amount", "dti_policy_exception",
            "policy_override_requested", "low_credit_score",
        }

    def test_high_loan_amount_triggers_above_50l(self, engine):
        matched = engine.evaluate({"loan_amount": 5_500_000})
        assert any(r.id == "high_loan_amount" for r in matched)

    def test_high_loan_amount_does_not_trigger_below_50l(self, engine):
        matched = engine.evaluate({"loan_amount": 3_000_000})
        assert not any(r.id == "high_loan_amount" for r in matched)

    def test_low_credit_score_triggers_below_650(self, engine):
        matched = engine.evaluate({"credit_score_assessment": {"credit_score": 610}})
        assert any(r.id == "low_credit_score" for r in matched)

    def test_policy_override_is_critical_severity(self, engine):
        matched = engine.evaluate({"policy_override_requested": True})
        assert engine.highest_severity(matched) == "critical"

    def test_no_rules_match_clean_context(self, engine):
        matched = engine.evaluate({"loan_amount": 100000, "credit_score_assessment": {"credit_score": 800}})
        assert matched == []

    def test_multiple_rules_can_match_simultaneously(self, engine):
        matched = engine.evaluate({
            "loan_amount": 6_000_000,
            "credit_score_assessment": {"credit_score": 600},
        })
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
        task = manager.check_and_create("sess-1", {"loan_amount": 10000}, "Approve")
        assert task is None

    def test_trigger_creates_pending_task(self, manager):
        task = manager.check_and_create("sess-2", {"loan_amount": 6_000_000}, "Recommend approval")
        assert task is not None
        assert task.status.value == "pending"
        assert manager.store.get(task.task_id).status.value == "pending"

    def test_pending_list_reflects_store(self, manager):
        manager.check_and_create("sess-3", {"loan_amount": 6_000_000}, "rec 1")
        manager.check_and_create("sess-4", {"loan_amount": 7_000_000}, "rec 2")
        assert len(manager.pending()) == 2

    def test_approve_resolves_task_and_removes_from_pending(self, manager):
        task = manager.check_and_create("sess-5", {"loan_amount": 6_000_000}, "rec")
        manager.review(task.task_id, decision="approve", decided_by="credit_head_1", comments="ok")
        assert manager.store.get(task.task_id).status.value == "approved"
        assert task.task_id not in [t.task_id for t in manager.pending()]

    def test_reject_resolves_task(self, manager):
        task = manager.check_and_create("sess-6", {"loan_amount": 6_000_000}, "rec")
        manager.review(task.task_id, decision="reject", decided_by="credit_head_1", comments="too risky")
        assert manager.store.get(task.task_id).status.value == "rejected"

    def test_double_review_raises(self, manager):
        task = manager.check_and_create("sess-7", {"loan_amount": 6_000_000}, "rec")
        manager.review(task.task_id, decision="approve", decided_by="a", comments=None)
        with pytest.raises(ValueError):
            manager.review(task.task_id, decision="approve", decided_by="b", comments=None)

    def test_review_unknown_task_raises(self, manager):
        with pytest.raises(KeyError):
            manager.review("nonexistent-id", decision="approve", decided_by="x", comments=None)

    def test_review_invalid_decision_raises(self, manager):
        task = manager.check_and_create("sess-8", {"loan_amount": 6_000_000}, "rec")
        with pytest.raises(ValueError):
            manager.review(task.task_id, decision="maybe", decided_by="x", comments=None)

    def test_task_persists_across_new_store_instance(self, manager):
        task = manager.check_and_create("sess-9", {"loan_amount": 6_000_000}, "rec")
        reopened_store = HITLStore(db_path=manager.store.db_path)
        assert reopened_store.get(task.task_id).status.value == "pending"