# FILE: tests/test_role_based_rag.py
"""Zero-leakage test suite for role-based RAG (Section 3.6, Week 8).
Section 4's acceptance threshold is 0% role-filter leakage -- these tests
exercise the pre-retrieval filter (rbac/filter.py), the post-retrieval
validator (rbac/validator.py), and the audit log (rbac/audit.py) against
every role, including an explicit full leakage matrix rather than a
sample.
"""
import os
import tempfile

import pytest

from rag.filters import matches_filters
from rbac.audit import log_retrieval, read_audit_log
from rbac.filter import build_role_filter, merge_filters
from rbac.role_registry import RoleRegistry
from rbac.validator import validate_no_leakage, RoleLeakageError

ALL_DOC_TYPES = ["policy", "circular", "memo", "audit"]


@pytest.fixture
def registry():
    return RoleRegistry("config/roles.yaml")


class TestRoleRegistry:
    def test_all_four_roles_load(self, registry):
        assert set(registry.roles) == {
            "junior_analyst", "senior_underwriter", "credit_head", "auditor",
        }

    def test_unknown_role_falls_back_to_fail_closed_default(self, registry):
        role = registry.get("nonexistent_role")
        for doc_type in ALL_DOC_TYPES:
            assert role.permits(doc_type) is False

    @pytest.mark.parametrize("doc_type,expected", [
        ("policy", True), ("circular", True), ("memo", False), ("audit", False),
    ])
    def test_junior_analyst_permissions(self, registry, doc_type, expected):
        assert registry.get("junior_analyst").permits(doc_type) is expected

    @pytest.mark.parametrize("doc_type,expected", [
        ("policy", True), ("circular", True), ("memo", True), ("audit", False),
    ])
    def test_senior_underwriter_permissions(self, registry, doc_type, expected):
        assert registry.get("senior_underwriter").permits(doc_type) is expected

    @pytest.mark.parametrize("doc_type", ALL_DOC_TYPES)
    def test_credit_head_has_full_access(self, registry, doc_type):
        assert registry.get("credit_head").permits(doc_type) is True

    @pytest.mark.parametrize("doc_type", ALL_DOC_TYPES)
    def test_auditor_has_full_read_access(self, registry, doc_type):
        assert registry.get("auditor").permits(doc_type) is True

    def test_only_credit_head_can_request_hitl_override(self, registry):
        assert registry.get("credit_head").can_request_hitl_override is True
        assert registry.get("auditor").can_request_hitl_override is False
        assert registry.get("junior_analyst").can_request_hitl_override is False
        assert registry.get("senior_underwriter").can_request_hitl_override is False


class TestPreRetrievalFilter:
    def test_junior_analyst_filter_excludes_memo_and_audit(self, registry):
        rf = build_role_filter("junior_analyst", registry)
        assert set(rf["doc_type"]["$in"]) == {"policy", "circular"}

    def test_merge_filters_role_wins_over_caller_supplied_doc_type(self, registry):
        rf = build_role_filter("junior_analyst", registry)
        merged = merge_filters(rf, {"doc_type": "audit", "jurisdiction": "IN"})
        # caller tried to widen access to 'audit' -- role filter must win
        assert merged["doc_type"] == {"$in": ["policy", "circular"]}
        assert merged["jurisdiction"] == "IN"

    def test_filter_applied_to_a_mixed_corpus_returns_only_allowed_types(self, registry):
        corpus = [
            {"doc_type": "policy"}, {"doc_type": "circular"},
            {"doc_type": "memo"}, {"doc_type": "audit"},
        ]
        rf = build_role_filter("junior_analyst", registry)
        surviving = [c for c in corpus if matches_filters(c, rf)]
        assert {c["doc_type"] for c in surviving} == {"policy", "circular"}


class TestPostRetrievalValidatorZeroLeakage:
    """Explicit zero-leakage matrix: every role x every restricted doc_type
    combination must be caught."""

    @pytest.mark.parametrize("role_name,restricted_type", [
        ("junior_analyst", "memo"),
        ("junior_analyst", "audit"),
        ("senior_underwriter", "audit"),
    ])
    def test_restricted_chunk_is_caught(self, registry, role_name, restricted_type):
        chunks = [{"text": "x", "metadata": {"doc_type": restricted_type, "chunk_id": "leak1"}}]
        with pytest.raises(RoleLeakageError):
            validate_no_leakage(role_name, chunks, registry, raise_on_leak=True)

    def test_allowed_chunks_pass_through_unchanged(self, registry):
        chunks = [
            {"text": "x", "metadata": {"doc_type": "policy", "chunk_id": "p1"}},
            {"text": "y", "metadata": {"doc_type": "circular", "chunk_id": "c1"}},
        ]
        result = validate_no_leakage("junior_analyst", chunks, registry)
        assert len(result) == 2

    def test_sanitize_mode_drops_without_raising(self, registry):
        chunks = [
            {"text": "x", "metadata": {"doc_type": "policy", "chunk_id": "p1"}},
            {"text": "y", "metadata": {"doc_type": "audit", "chunk_id": "a1"}},
        ]
        result = validate_no_leakage("junior_analyst", chunks, registry, raise_on_leak=False)
        assert [c["metadata"]["chunk_id"] for c in result] == ["p1"]

    def test_full_matrix_zero_leakage(self, registry):
        """For every role, feed all four doc_types through the validator in
        sanitize mode and assert only exactly the permitted set survives."""
        all_chunks = [
            {"text": t, "metadata": {"doc_type": t, "chunk_id": t}} for t in ALL_DOC_TYPES
        ]
        for role_name, role in registry.roles.items():
            survived = validate_no_leakage(role_name, all_chunks, registry, raise_on_leak=False)
            survived_types = {c["metadata"]["doc_type"] for c in survived}
            expected = {dt for dt in ALL_DOC_TYPES if role.permits(dt)}
            assert survived_types == expected, f"leakage mismatch for role={role_name}"


class TestAuditLog:
    def setup_method(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # log_retrieval creates it on first write

    def teardown_method(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_log_retrieval_writes_a_record(self):
        record = log_retrieval(
            role_name="junior_analyst", session_id="s1", query="what is the LTV policy?",
            allowed_doc_types=["policy", "circular"], returned_chunk_ids=["p1", "c1"],
            log_path=self.path,
        )
        assert record["role"] == "junior_analyst"
        assert record["returned_count"] == 2

    def test_log_retrieval_records_leaked_and_dropped_ids(self):
        log_retrieval(
            role_name="junior_analyst", session_id="s1", query="q",
            allowed_doc_types=["policy"], returned_chunk_ids=["p1"],
            leaked_and_dropped_chunk_ids=["a1"], log_path=self.path,
        )
        logs = read_audit_log(self.path)
        assert logs[0]["leaked_and_dropped_chunk_ids"] == ["a1"]

    def test_read_audit_log_respects_limit(self):
        for i in range(5):
            log_retrieval(
                role_name="junior_analyst", session_id=f"s{i}", query="q",
                allowed_doc_types=["policy"], returned_chunk_ids=[], log_path=self.path,
            )
        assert len(read_audit_log(self.path, limit=2)) == 2

    def test_read_audit_log_missing_file_returns_empty(self):
        assert read_audit_log("/tmp/does_not_exist_audit.jsonl") == []


def test_end_to_end_pipeline_no_leakage_for_junior_analyst(registry):
    """Simulates the full pre-retrieval + post-retrieval pipeline for a
    corpus mixing all doc_types."""
    corpus = [
        {"text": "policy text", "metadata": {"doc_type": "policy", "chunk_id": "p1"}},
        {"text": "circular text", "metadata": {"doc_type": "circular", "chunk_id": "c1"}},
        {"text": "memo text", "metadata": {"doc_type": "memo", "chunk_id": "m1"}},
        {"text": "audit text", "metadata": {"doc_type": "audit", "chunk_id": "a1"}},
    ]
    role_filter = build_role_filter("junior_analyst", registry)
    pre_filtered = [c for c in corpus if matches_filters(c["metadata"], role_filter)]
    post_validated = validate_no_leakage("junior_analyst", pre_filtered, registry)
    returned_ids = {c["metadata"]["chunk_id"] for c in post_validated}
    assert returned_ids == {"p1", "c1"}
    assert "m1" not in returned_ids
    assert "a1" not in returned_ids