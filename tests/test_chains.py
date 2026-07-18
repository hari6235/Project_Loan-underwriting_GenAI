# FILE: tests/test_chains.py
"""Tests for the LCEL orchestration layer (Section 3.2, Week 8).

Pure-logic pieces (intent classification, filter-building) are tested
without any LangChain dependency. Anything touching langchain_core
Runnables/messages is skipped automatically if langchain_core isn't
installed in the environment running pytest.
"""
import pytest


def test_classify_intent_greeting():
    from chains.router import _classify_intent
    assert _classify_intent("hi") == "greeting"
    assert _classify_intent("Hello!") == "greeting"
    assert _classify_intent("  good morning  ") == "greeting"


def test_classify_intent_full_agent_for_substantive_query():
    from chains.router import _classify_intent
    assert _classify_intent("What is the max LTV for a home loan above 75L?") == "full_agent"
    assert _classify_intent("Calculate DTI for income 90000 and EMI 30000") == "full_agent"


def test_build_doc_type_filters_from_tool_call_args():
    langchain_core = pytest.importorskip("langchain_core")  # noqa: F841
    from chains.tool_chain import _build_doc_type_filters

    assert _build_doc_type_filters({}) is None
    assert _build_doc_type_filters({"doc_type": "policy"}) == {"doc_type": "policy"}
    assert _build_doc_type_filters({"doc_type": "policy", "jurisdiction": "IN"}) == {
        "doc_type": "policy", "jurisdiction": "IN",
    }


def test_history_to_messages_roundtrip():
    langchain_core = pytest.importorskip("langchain_core")  # noqa: F841
    from chains.tool_chain import _history_to_messages
    from langchain_core.messages import HumanMessage, AIMessage

    history = [
        {"user": "What is DTI?", "assistant": '{"response": "Debt-to-Income ratio.", "type": "llm_response"}'},
        {"user": "Thanks", "assistant": "You're welcome"},
    ]
    messages = _history_to_messages(history)
    assert len(messages) == 4
    assert isinstance(messages[0], HumanMessage) and messages[0].content == "What is DTI?"
    assert isinstance(messages[1], AIMessage) and messages[1].content == "Debt-to-Income ratio."
    assert isinstance(messages[3], AIMessage) and messages[3].content == "You're welcome"


def test_history_to_messages_handles_malformed_json_gracefully():
    langchain_core = pytest.importorskip("langchain_core")  # noqa: F841
    from chains.tool_chain import _history_to_messages

    history = [{"user": "hi", "assistant": "not valid json {{{"}]
    messages = _history_to_messages(history)
    assert messages[1].content == "not valid json {{{"


class TestHITLChainGating:
    """hitl_chain.py must gate a turn based on decision_context returned
    by tool_chain -- these tests stub tool_chain.invoke() so no real LLM
    call is needed."""

    def test_no_decision_context_passes_through_unchanged(self, monkeypatch):
        langchain_core = pytest.importorskip("langchain_core")  # noqa: F841
        import chains.hitl_chain as hitl_chain_mod

        class StubToolChain:
            def invoke(self, payload, config=None):
                return {"type": "llm_response", "response": "hello", "decision_context": {}}

        monkeypatch.setattr(hitl_chain_mod, "tool_chain", StubToolChain())

        from hitl.manager import HITLManager
        from hitl.store import HITLStore
        from hitl.triggers import TriggerEngine
        import tempfile, os

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        manager = HITLManager(store=HITLStore(db_path=path), trigger_engine=TriggerEngine("config/hitl_rules.yaml"))

        chain = hitl_chain_mod.build_hitl_chain(manager)
        result = chain.invoke({"input": "hi", "session_id": "s1"})
        assert result["type"] == "llm_response"
        os.remove(path)

    def test_triggering_decision_context_pauses_for_approval(self, monkeypatch):
        langchain_core = pytest.importorskip("langchain_core")  # noqa: F841
        import chains.hitl_chain as hitl_chain_mod

        class StubToolChain:
            def invoke(self, payload, config=None):
                return {
                    "type": "tool_response",
                    "response": "Recommend approving 60L loan",
                    "decision_context": {"loan_amount": 6_000_000},
                }

        monkeypatch.setattr(hitl_chain_mod, "tool_chain", StubToolChain())

        from hitl.manager import HITLManager
        from hitl.store import HITLStore
        from hitl.triggers import TriggerEngine
        import tempfile, os

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        manager = HITLManager(store=HITLStore(db_path=path), trigger_engine=TriggerEngine("config/hitl_rules.yaml"))

        chain = hitl_chain_mod.build_hitl_chain(manager)
        result = chain.invoke({"input": "approve 60L loan for A-101", "session_id": "s2"})
        assert result["type"] == "pending_approval"
        assert "hitl_task_id" in result
        assert manager.store.get(result["hitl_task_id"]).status.value == "pending"
        os.remove(path)


def test_fallback_chain_is_wired_with_with_fallbacks():
    langchain_core = pytest.importorskip("langchain_core")  # noqa: F841
    from chains.router import full_agent_chain_with_fallback
    # .with_fallbacks() returns a RunnableWithFallbacks; just assert the
    # composition succeeded and exposes the expected attribute.
    assert hasattr(full_agent_chain_with_fallback, "fallbacks")
    assert len(full_agent_chain_with_fallback.fallbacks) == 1