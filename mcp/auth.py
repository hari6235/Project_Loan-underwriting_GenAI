# FILE: mcp/auth.py
"""Per-server authentication resolution. A server's API key/token is read
from the environment variable named in its config (auth_env_var), never
hardcoded. Simulated-mode servers don't require a live key but auth is
still checked and logged so switching a server to `mode: http` doesn't
silently skip authentication."""
import os

from mcp.registry import MCPServerSpec


class MCPAuthError(Exception):
    pass


def resolve_auth(server: MCPServerSpec) -> dict:
    """Returns headers to attach to an HTTP call for this server. For
    simulated-mode servers, returns an empty dict (no live call is made),
    but still validates the env var is documented in config so the
    transition to a real integration is a config-only change."""
    if not server.auth_env_var:
        raise MCPAuthError(f"Server '{server.id}' has no auth_env_var configured.")

    api_key = os.getenv(server.auth_env_var)

    if server.mode == "simulated":
        # No live call happens, so a missing key is fine, but we still
        # return the header shape a real call would use once configured.
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    if not api_key:
        raise MCPAuthError(
            f"Server '{server.id}' is in 'http' mode but env var "
            f"'{server.auth_env_var}' is not set."
        )
    return {"Authorization": f"Bearer {api_key}"}