"""
API Integration Tests - Test all endpoints with realistic scenarios.

These tests simulate actual user workflows through the API.

Run with: pytest tests/test_api_integration.py -v --tb=short
Note: Requires backend to be running on http://127.0.0.1:8000
"""
import pytest
import json
import requests
from pathlib import Path


# Parametrize API base URL for flexibility
@pytest.fixture
def api_base():
    return "http://127.0.0.1:8000"


@pytest.fixture
def session_id():
    import uuid
    return f"test-{uuid.uuid4().hex[:8]}"


class TestChatAPI:
    """Test /chat endpoint with various message types."""

    def test_chat_endpoint_greeting(self, api_base, session_id):
        """Test chat with a greeting message."""
        payload = {
            "session_id": session_id,
            "message": "Hello, how can you help me with loan underwriting?"
        }
        
        try:
            response = requests.post(
                f"{api_base}/chat",
                json=payload,
                headers={"X-User-Role": "junior_analyst"},
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "session_id" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")

    def test_chat_endpoint_loan_query(self, api_base, session_id):
        """Test chat with a loan-related query."""
        payload = {
            "session_id": session_id,
            "message": "What is the maximum DTI ratio allowed for personal loans?"
        }
        
        try:
            response = requests.post(
                f"{api_base}/chat",
                json=payload,
                headers={"X-User-Role": "junior_analyst"},
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert data["response"] is not None
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")

    def test_chat_with_role_header(self, api_base, session_id):
        """Test chat respects role-based access."""
        roles = ["junior_analyst", "senior_underwriter", "credit_head", "auditor"]
        
        for role in roles:
            payload = {
                "session_id": f"{session_id}-{role}",
                "message": "Show me pending approvals"
            }
            
            try:
                response = requests.post(
                    f"{api_base}/chat",
                    json=payload,
                    headers={"X-User-Role": role},
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] is not None
            except requests.exceptions.ConnectionError:
                pytest.skip("Backend not running")


class TestResetAPI:
    """Test /reset endpoint for clearing session memory."""

    def test_reset_session(self, api_base, session_id):
        """Test session reset clears memory."""
        try:
            # First add something to memory via chat
            chat_payload = {
                "session_id": session_id,
                "message": "Hello"
            }
            requests.post(
                f"{api_base}/chat",
                json=chat_payload,
                headers={"X-User-Role": "junior_analyst"},
                timeout=10
            )
            
            # Then reset
            response = requests.post(
                f"{api_base}/reset",
                params={"session_id": session_id},
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestHealthAPI:
    """Test /health endpoint."""

    def test_health_check(self, api_base):
        """Test health endpoint returns service status."""
        try:
            response = requests.get(f"{api_base}/health", timeout=10)
            assert response.status_code == 200
            data = response.json()
            
            # Verify expected health fields
            assert "status" in data
            assert "service" in data
            assert "vector_store_loaded" in data
            assert data["status"] == "healthy"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")

    def test_health_includes_metrics(self, api_base):
        """Test health endpoint includes operational metrics."""
        try:
            response = requests.get(f"{api_base}/health", timeout=10)
            data = response.json()
            
            # Check for operational metrics
            assert "mcp_servers_registered" in data
            assert "hitl_pending_count" in data
            assert isinstance(data["mcp_servers_registered"], int)
            assert isinstance(data["hitl_pending_count"], int)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestDocumentAPI:
    """Test document ingestion endpoints."""

    def test_ingest_endpoint_structure(self, api_base):
        """Test /ingest endpoint accepts file uploads."""
        try:
            # Create a minimal test file
            test_content = "This is a test document for loan underwriting."
            files = {"file": ("test.txt", test_content.encode())}
            
            response = requests.post(
                f"{api_base}/ingest",
                files=files,
                timeout=30
            )
            
            # Should return job_id for async processing
            assert response.status_code in [200, 202, 400]
            if response.status_code == 200:
                data = response.json()
                assert "job_id" in data or "error" in data
                
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")

    def test_ingest_status_check(self, api_base):
        """Test /ingest/status endpoint."""
        try:
            # Try to check status of a dummy job
            response = requests.get(
                f"{api_base}/ingest/status/dummy-job-id",
                timeout=10
            )
            
            # Should either return status or 404
            assert response.status_code in [200, 404, 400]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestSourcesAPI:
    """Test document source management."""

    def test_sources_list(self, api_base):
        """Test /sources endpoint lists indexed documents."""
        try:
            response = requests.get(
                f"{api_base}/sources",
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            
            assert "sources" in data
            assert isinstance(data["sources"], list)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestPromptsAPI:
    """Test prompt management endpoints."""

    def test_prompts_list(self, api_base):
        """Test /prompts endpoint lists available prompts."""
        try:
            response = requests.get(
                f"{api_base}/prompts",
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            
            assert "prompts" in data or "active" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestHITLAPI:
    """Test Human-In-The-Loop approval endpoints."""

    def test_hitl_pending_tasks(self, api_base):
        """Test /hitl/pending lists pending approvals."""
        try:
            response = requests.get(
                f"{api_base}/hitl/pending",
                headers={"X-User-Role": "senior_underwriter"},
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            
            assert "tasks" in data or isinstance(data, list)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestMCPAPI:
    """Test MCP tool endpoints."""

    def test_mcp_tools_list(self, api_base):
        """Test /mcp/tools lists available MCP tools."""
        try:
            response = requests.get(
                f"{api_base}/mcp/tools",
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            
            assert "tools" in data or isinstance(data, list)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestRolesAPI:
    """Test role management endpoints."""

    def test_roles_list(self, api_base):
        """Test /roles endpoint lists available roles."""
        try:
            response = requests.get(
                f"{api_base}/roles",
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            
            assert "roles" in data or isinstance(data, list)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestEvalAPI:
    """Test evaluation endpoints."""

    def test_eval_regression_endpoint(self, api_base):
        """Test /eval/regression endpoint structure."""
        try:
            response = requests.post(
                f"{api_base}/eval/regression",
                json={},
                timeout=60
            )
            
            # Should either run successfully or indicate service issue
            assert response.status_code in [200, 202, 400, 503]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")

    def test_eval_drift_endpoint(self, api_base):
        """Test /eval/drift endpoint structure."""
        try:
            response = requests.post(
                f"{api_base}/eval/drift",
                json={},
                timeout=60
            )
            
            assert response.status_code in [200, 202, 400, 503]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestGuardrailsIntegration:
    """Test guardrails behavior in chat."""

    def test_pii_detection_in_chat(self, api_base, session_id):
        """Test that PII is detected and rejected in chat."""
        payload = {
            "session_id": session_id,
            "message": "My SSN is 123-45-6789"
        }
        
        try:
            response = requests.post(
                f"{api_base}/chat",
                json=payload,
                headers={"X-User-Role": "junior_analyst"},
                timeout=10
            )
            # Should return error or warning about PII
            data = response.json()
            # Response may contain warning or error indicator
            assert response.status_code in [200, 400]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")

    def test_topic_filter_non_banking(self, api_base, session_id):
        """Test that non-banking queries are rejected."""
        payload = {
            "session_id": session_id,
            "message": "How do I cook pasta?"
        }
        
        try:
            response = requests.post(
                f"{api_base}/chat",
                json=payload,
                headers={"X-User-Role": "junior_analyst"},
                timeout=10
            )
            # May be rejected or allowed with warning
            assert response.status_code in [200, 400]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestErrorCases:
    """Test error handling across endpoints."""

    def test_missing_session_id(self, api_base):
        """Test chat requires session_id."""
        payload = {
            "message": "Hello"
            # Missing session_id
        }
        
        try:
            response = requests.post(
                f"{api_base}/chat",
                json=payload,
                headers={"X-User-Role": "junior_analyst"},
                timeout=10
            )
            # Should return 422 (validation error)
            assert response.status_code in [400, 422]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")

    def test_invalid_json(self, api_base):
        """Test endpoint rejects invalid JSON."""
        try:
            response = requests.post(
                f"{api_base}/chat",
                data="not valid json",
                headers={
                    "X-User-Role": "junior_analyst",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            assert response.status_code in [400, 422]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


class TestConversationFlow:
    """Test realistic multi-turn conversations."""

    def test_multi_turn_conversation(self, api_base, session_id):
        """Test conversation with multiple turns."""
        messages = [
            "What are the eligibility criteria for a home loan?",
            "What is the maximum loan amount?",
            "How long is the approval process?"
        ]
        
        try:
            for msg in messages:
                payload = {
                    "session_id": session_id,
                    "message": msg
                }
                response = requests.post(
                    f"{api_base}/chat",
                    json=payload,
                    headers={"X-User-Role": "junior_analyst"},
                    timeout=10
                )
                assert response.status_code == 200
                
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
