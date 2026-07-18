# FILE: mcp/client.py
"""MCP client: discovers tools via the registry and invokes them, whether
backed by a real HTTP MCP server (`mode: http`) or a local simulated
handler (`mode: simulated`). The agent-facing contract
(mcp/tool_adapter.py) is identical either way -- callers never know or
care which mode a given server is in.
"""
from __future__ import annotations

import time

from mcp.auth import resolve_auth, MCPAuthError
from mcp.registry import MCPRegistry, MCPServerSpec, get_registry
from mcp.simulated_handlers import HANDLERS, MCPToolError
from utils.logger import get_logger

logger = get_logger("mcp.client")


class MCPInvocationError(Exception):
    def __init__(self, message: str, server_id: str | None = None, tool_name: str | None = None):
        super().__init__(message)
        self.server_id = server_id
        self.tool_name = tool_name


class MCPClient:
    def __init__(self, registry: MCPRegistry | None = None):
        self.registry = registry or get_registry()

    def health_check(self, server_id: str) -> bool:
        server = self.registry.servers.get(server_id)
        if not server:
            return False
        try:
            resolve_auth(server)
            if server.mode == "simulated":
                healthy = True
            else:
                healthy = self._http_health_check(server)
            self.registry.mark_health(server_id, healthy)
            return healthy
        except MCPAuthError as exc:
            self.registry.mark_health(server_id, False, str(exc))
            return False

    def _http_health_check(self, server: MCPServerSpec) -> bool:
        try:
            import httpx
            resp = httpx.get(f"{server.base_url}/health", timeout=server.timeout_seconds)
            return resp.status_code < 500
        except Exception as exc:
            logger.warning("Health check failed for server=%s: %s", server.id, exc)
            return False

    def invoke(self, tool_name: str, params: dict) -> dict:
        """Invoke an MCP tool by name. Retries transient failures up to
        server.max_retries times with linear backoff. Raises
        MCPInvocationError on exhaustion or on a hard validation error from
        the handler (validation errors are NOT retried -- retrying a bad
        request just wastes the retry budget)."""
        match = self.registry.find_tool(tool_name)
        if match is None:
            raise MCPInvocationError(f"No MCP tool registered with name '{tool_name}'", tool_name=tool_name)
        server, tool = match

        self._validate_required_params(tool.input_schema, params, tool_name)

        last_error: Exception | None = None
        attempts = max(1, server.max_retries + 1)
        for attempt in range(1, attempts + 1):
            start = time.monotonic()
            try:
                if server.mode == "simulated":
                    result = self._invoke_simulated(tool.handler, params)
                else:
                    result = self._invoke_http(server, tool, params)
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.info(
                    "MCP invoke ok server=%s tool=%s attempt=%d elapsed_ms=%.1f",
                    server.id, tool_name, attempt, elapsed_ms,
                )
                self.registry.mark_health(server.id, True)
                return {"server_id": server.id, "tool": tool_name, "result": result, "attempts": attempt}
            except MCPToolError as exc:
                # Bad input -- don't retry, surface immediately.
                self.registry.mark_health(server.id, False, str(exc))
                raise MCPInvocationError(str(exc), server_id=server.id, tool_name=tool_name) from exc
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "MCP invoke failed server=%s tool=%s attempt=%d/%d error=%s",
                    server.id, tool_name, attempt, attempts, exc,
                )
                self.registry.mark_health(server.id, False, str(exc))

        raise MCPInvocationError(
            f"Tool '{tool_name}' failed after {attempts} attempt(s): {last_error}",
            server_id=server.id, tool_name=tool_name,
        )

    @staticmethod
    def _validate_required_params(input_schema: dict, params: dict, tool_name: str) -> None:
        missing = [
            name for name, spec in (input_schema or {}).items()
            if spec.get("required") and params.get(name) is None
        ]
        if missing:
            raise MCPInvocationError(
                f"Missing required parameter(s) for '{tool_name}': {', '.join(missing)}",
                tool_name=tool_name,
            )

    @staticmethod
    def _invoke_simulated(handler_path: str, params: dict) -> dict:
        handler = HANDLERS.get(handler_path)
        if handler is None:
            raise MCPInvocationError(f"No simulated handler registered for '{handler_path}'")
        return handler(**params)

    @staticmethod
    def _invoke_http(server: MCPServerSpec, tool, params: dict) -> dict:
        import httpx
        headers = resolve_auth(server)
        resp = httpx.post(
            f"{server.base_url}/tools/{tool.name}/invoke",
            json=params,
            headers=headers,
            timeout=server.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()


_client: MCPClient | None = None


def get_client() -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient()
    return _client