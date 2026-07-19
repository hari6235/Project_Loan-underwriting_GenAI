# MCP Integration

## Goal

Enable the LangChain agent to discover and invoke external tools exposed as
standardised MCP server endpoints, rather than hardcoding tool integrations.
The agent treats MCP tools identically to local tools — it selects them
based on query context.

## Components

| File | Responsibility |
|---|---|
| `mcp/registry.py` | Loads and parses `config/mcp_servers.yaml`; exposes the list of configured servers and their tool schemas to the rest of the app. |
| `mcp/client.py` | MCP client adapter — discovers available tools, sends invocation requests, applies per-server timeout and retry policy. |
| `mcp/auth.py` | Resolves per-server authentication (API keys via `auth_env_var`) before a call is made. |
| `mcp/tool_adapter.py` | Translates MCP tool schemas into LangChain-compatible tool definitions so `tools/langchain_tools.py` can bind them alongside local tools. |
| `mcp/simulated_handlers.py` | Deterministic, in-repo handlers backing the `simulated` server mode (see below). |

## Server configuration

Servers are declared in `config/mcp_servers.yaml`. Three servers are
configured and functional out of the box (minimum required: 2):

1. **`credit_bureau_lookup`** — `fetch_credit_report(pan)`: returns credit
   score, active tradelines, recent enquiries, and bureau-reported defaults.
2. **`income_verification`** — `verify_income(pan, declared_monthly_income)`:
   verifies declared income against payroll/ITR data, returns verified
   income and variance.
3. **`property_valuation`** — `estimate_property_value(...)`: estimates fair
   market value for collateral property.

Each server entry specifies:

```yaml
servers:
  credit_bureau_lookup:
    mode: simulated            # or "http" for a live MCP endpoint
    base_url: "https://api.creditbureau.example.com/v1"
    auth_env_var: "CREDIT_BUREAU_API_KEY"
    timeout_seconds: 3
    max_retries: 2
    tools:
      - name: fetch_credit_report
        input_schema: { pan: { type: string, required: true } }
        handler: credit_bureau.fetch_credit_report
```

## `simulated` vs `http` mode

No live third-party contract exists for these banking data sources in a
course project, so each server runs in `mode: simulated` by default: calls
are routed to `mcp/simulated_handlers.py`, which performs real, deterministic
computation (validation, lookup, math) against the **same request/response
schema** a live `http` server would use — it is not a hardcoded canned
response. Switching a server to `mode: http` (pointing `base_url` at a real
endpoint and setting the corresponding env var) requires **no changes** to
the agent, the tool-calling contract, or the chain code, since
`mcp/client.py` dispatches on `mode` internally.

## Runtime flow

1. `mcp/registry.py` reads `config/mcp_servers.yaml` at startup.
2. `mcp/tool_adapter.py` converts each declared tool into a LangChain tool
   object and registers it in `tools/tool_registry.py` alongside the
   deterministic tools (DTI, credit score, policy flag).
3. When the agent selects an MCP-backed tool, `mcp/client.py`:
   - resolves auth via `mcp/auth.py`,
   - dispatches to the live endpoint (`http` mode) or the local handler
     (`simulated` mode),
   - enforces `timeout_seconds` and `max_retries` from the server config.
4. Results flow back into the tool chain (`chains/tool_chain.py`) exactly
   like a local tool result, and become part of the `decision_context`
   used for HITL rule evaluation.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /mcp/tools` | Lists all discovered MCP tools across configured servers. |
| `POST /mcp/invoke` | Directly invokes a named MCP tool with a JSON payload (used for manual testing / the Streamlit MCP tools tab). |

## Testing

`tests/test_mcp_integration.py` covers: server/tool discovery from
`config/mcp_servers.yaml`, simulated-handler correctness for each of the
three servers, and error handling for timeout/retry paths.

## Adding a new MCP server

1. Add a new entry under `servers:` in `config/mcp_servers.yaml` with its
   tool schema.
2. If running in `simulated` mode, add a matching handler function in
   `mcp/simulated_handlers.py`.
3. If running in `http` mode, set the `auth_env_var` value in `.env`.
4. No code changes are needed in `chains/` or `tools/tool_registry.py` — the
   tool is picked up automatically via `mcp/tool_adapter.py` at startup.