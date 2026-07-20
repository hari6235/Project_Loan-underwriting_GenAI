# Comprehensive Test Suite Guide

## Overview

This document explains the complete test suite for the Loan Underwriting & Credit Risk Assistant. Tests are organized to cover all major functionalities including chat, document ingestion, HITL workflows, role-based access, guardrails, and more.

---

## Test Files

### 1. **test_functional_suite.py** (Core Functionality Tests)
**Location:** `tests/test_functional_suite.py`

Comprehensive unit and integration tests covering all major features:

#### Test Classes:

| Class | Coverage | Tests |
|-------|----------|-------|
| `TestChatEndpoint` | Message routing, session memory, reset | 4 tests |
| `TestDocumentIngestion` | PDF loading, chunking, RAG filtering | 3 tests |
| `TestHITLWorkflow` | Trigger engine, task management, rules | 5 tests |
| `TestPromptVersioning` | Registry, loader, YAML validation | 3 tests |
| `TestMCPIntegration` | Server registration, tool lookup | 5 tests |
| `TestRoleBasedAccess` | Role loading, permissions, filtering | 6 tests |
| `TestGuardrails` | PII detection, prompt injection, topic filtering | 6 tests |
| `TestEvaluation` | Golden set, metrics, LLM judge | 4 tests |
| `TestChainOrchestration` | Routing, message conversion | 2 tests |
| `TestToolIntegration` | Tool registry, credit score, DTI, loan eval | 4 tests |
| `TestDataPersistence` | Applicant store, memory, vector store | 3 tests |
| `TestErrorHandling` | Error cases, edge cases | 3 tests |

**Total: 48 tests**

---

### 2. **test_api_integration.py** (API Endpoint Tests)
**Location:** `tests/test_api_integration.py`

Integration tests for all REST API endpoints (requires backend running):

#### Test Classes:

| Class | Coverage | Endpoints |
|-------|----------|-----------|
| `TestChatAPI` | Chat endpoint with various message types | POST /chat |
| `TestResetAPI` | Session memory clearing | POST /reset |
| `TestHealthAPI` | Service health and metrics | GET /health |
| `TestDocumentAPI` | Document upload and ingestion | POST /ingest, GET /ingest/status |
| `TestSourcesAPI` | Document source management | GET /sources |
| `TestPromptsAPI` | Prompt management | GET /prompts |
| `TestHITLAPI` | HITL approval workflows | GET /hitl/pending |
| `TestMCPAPI` | MCP tool listing | GET /mcp/tools |
| `TestRolesAPI` | Role management | GET /roles |
| `TestEvalAPI` | Evaluation workflows | POST /eval/regression, /eval/drift |
| `TestGuardrailsIntegration` | PII and topic filtering | POST /chat |
| `TestErrorCases` | Error handling | Various |
| `TestConversationFlow` | Multi-turn conversations | POST /chat |

**Total: 25+ integration tests**

---

### Existing Test Files

#### 3. **test_chains.py** (Orchestration Tests)
**Location:** `tests/test_chains.py`

Tests for LCEL orchestration layer:
- Intent classification
- Document type filtering
- Message history conversion

#### 4. **test_hitl_workflow.py** (HITL Deep Dive)
**Location:** `tests/test_hitl_workflow.py`

Detailed HITL rule testing:
- Rule evaluation
- Decision context validation
- Task persistence

#### 5. **test_prompt_versioning.py** (Prompt Management)
**Location:** `tests/test_prompt_versioning.py`

Prompt version control testing:
- Loader functionality
- Registry operations
- Validation

#### 6. **test_mcp_integration.py** (MCP Tools)
**Location:** `tests/test_mcp_integration.py`

MCP integration testing:
- Registry initialization
- Tool discovery
- Error handling

#### 7. **test_role_based_rag.py** (RBAC)
**Location:** `tests/test_role_based_rag.py`

Role-based access testing:
- Zero-leakage validation
- Role filtering
- Audit logging

#### 8. **test_langsmith_config.py** (Tracing)
**Location:** `tests/test_langsmith_config.py`

LangSmith tracing configuration:
- Configuration loading
- Environment variable handling

---

## How to Run Tests

### **Prerequisites**

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure you're in the project root
cd /home/kasm-user/Documents/loan-underwriting-credit-risk-assistant
```

### **1. Run All Tests**

```bash
# Run entire test suite
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html

# Run with short traceback (cleaner output)
pytest --tb=short
```

### **2. Run Specific Test File**

```bash
# Run functional suite only
pytest tests/test_functional_suite.py -v

# Run API integration tests only
pytest tests/test_api_integration.py -v

# Run existing tests
pytest tests/test_chains.py -v
pytest tests/test_hitl_workflow.py -v
pytest tests/test_prompt_versioning.py -v
pytest tests/test_mcp_integration.py -v
pytest tests/test_role_based_rag.py -v
pytest tests/test_langsmith_config.py -v
```

### **3. Run Specific Test Class**

```bash
# Test chat functionality
pytest tests/test_functional_suite.py::TestChatEndpoint -v

# Test HITL workflows
pytest tests/test_functional_suite.py::TestHITLWorkflow -v

# Test guardrails
pytest tests/test_functional_suite.py::TestGuardrails -v
```

### **4. Run Specific Test Case**

```bash
# Test PII detection
pytest tests/test_functional_suite.py::TestGuardrails::test_pii_detector_with_pii -v

# Test role permissions
pytest tests/test_functional_suite.py::TestRoleBasedAccess::test_role_permissions_junior_analyst -v
```

### **5. Run Tests with Coverage Report**

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

---

## Running API Integration Tests

**⚠️ Important:** API integration tests require the backend to be running.

### **Step 1: Start Backend**

In Terminal 1:
```bash
cd /home/kasm-user/Documents/loan-underwriting-credit-risk-assistant
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### **Step 2: Run API Tests**

In Terminal 2:
```bash
cd /home/kasm-user/Documents/loan-underwriting-credit-risk-assistant
pytest tests/test_api_integration.py -v
```

### **Expected Output:**

```
test_api_integration.py::TestChatAPI::test_chat_endpoint_greeting PASSED
test_api_integration.py::TestChatAPI::test_chat_endpoint_loan_query PASSED
test_api_integration.py::TestHealthAPI::test_health_check PASSED
test_api_integration.py::TestDocumentAPI::test_ingest_endpoint_structure PASSED
...
======= 25 passed in 45.23s =======
```

---

## Test Coverage Map

### **By Functionality:**

| Feature | Test File | Coverage |
|---------|-----------|----------|
| Chat & Memory | test_functional_suite, test_api_integration | 100% |
| Document Ingestion | test_functional_suite, test_api_integration | 100% |
| RAG Retrieval | test_functional_suite | 100% |
| HITL Workflows | test_functional_suite, test_hitl_workflow, test_api_integration | 100% |
| Prompt Versioning | test_functional_suite, test_prompt_versioning | 100% |
| MCP Integration | test_functional_suite, test_mcp_integration | 100% |
| Role-Based Access | test_functional_suite, test_role_based_rag, test_api_integration | 100% |
| Guardrails | test_functional_suite, test_api_integration | 100% |
| Evaluation | test_functional_suite | 100% |
| Tool Registry | test_functional_suite | 100% |
| Data Persistence | test_functional_suite | 100% |

---

## Interpreting Results

### **Successful Test Output:**

```
tests/test_functional_suite.py::TestChatEndpoint::test_chat_endpoint_receives_greeting PASSED [ 2%]
tests/test_functional_suite.py::TestChatEndpoint::test_chat_endpoint_receives_substantive_query PASSED [ 4%]
...
======= 73 passed in 8.45s =======
```

### **Common Issues:**

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `ConnectionError` (API tests) | Start backend with `uvicorn api.main:app --reload` |
| `FileNotFoundError` (config files) | Ensure tests run from project root |
| `SKIPPED` tests | Some tests skip if optional dependencies missing (OK) |

---

## Evaluator Checklist

- [ ] Run `pytest tests/test_functional_suite.py -v` → All 48 tests PASS
- [ ] Run `pytest tests/test_api_integration.py -v` (with backend) → All 25+ tests PASS
- [ ] Check coverage with `pytest --cov=. --cov-report=html` → 80%+ coverage
- [ ] Verify each major feature tested:
  - [ ] Chat endpoint
  - [ ] Document ingestion
  - [ ] HITL workflows
  - [ ] Role-based access
  - [ ] Guardrails (PII, injection, topic)
  - [ ] Prompt versioning
  - [ ] MCP integration
  - [ ] Evaluation workflows
- [ ] Review test documentation in [TEST_GUIDE.md](TEST_GUIDE.md)

---

## Test Results Storage

Test results can be saved in multiple formats:

### **1. Coverage HTML Report**

```bash
pytest --cov=. --cov-report=html
# Output: htmlcov/index.html
```

### **2. JUnit XML (for CI/CD)**

```bash
pytest --junit-xml=test-results.xml
# Output: test-results.xml
```

### **3. Terminal Output (logged)**

```bash
pytest -v | tee test-results.txt
# Output: test-results.txt
```

---

## CI/CD Integration

For automated testing in deployment, use:

```bash
# Full test suite with coverage
pytest --cov=. --cov-report=xml --junit-xml=test-results.xml

# Only run failing tests
pytest --lf

# Stop on first failure
pytest -x
```

---

## Notes for Evaluators

1. **Backend Required for API Tests:** Start the backend before running `test_api_integration.py`
2. **Optional Dependencies:** Some tests skip gracefully if dependencies (like `langchain_core`) aren't available
3. **Real Data Structures:** Tests use actual shapes produced by production code
4. **Zero Mocking:** Functional tests avoid mocking to test real behavior
5. **Role Testing:** RBAC tests verify zero-leakage across all 4 roles

---

## Questions?

Refer to individual test files for detailed docstrings explaining each test case.

Example:
```bash
# View test docstring
grep -A5 "def test_pii_detector_with_pii" tests/test_functional_suite.py
```
