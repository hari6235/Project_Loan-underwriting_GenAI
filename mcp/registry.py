# FILE: mcp/registry.py
"""Loads config/mcp_servers.yaml into typed server definitions and tracks
live health/connection status for each registered server."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import yaml

DEFAULT_CONFIG_PATH = "config/mcp_servers.yaml"


@dataclass
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict
    handler: str


@dataclass
class MCPServerSpec:
    id: str
    mode: str
    description: str
    base_url: str
    auth_env_var: str
    timeout_seconds: float
    max_retries: int
    tools: list[MCPToolSpec] = field(default_factory=list)
    # runtime health state
    status: str = "unknown"          # unknown | healthy | unhealthy
    last_checked_at: float | None = None
    last_error: str | None = None


class MCPRegistry:
    """Parses config/mcp_servers.yaml once at startup. Call reload() to
    hot-reload after editing the YAML without restarting the process."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.servers: dict[str, MCPServerSpec] = {}
        self.reload()

    def reload(self) -> None:
        with open(self.config_path, "r") as f:
            raw = yaml.safe_load(f) or {}

        servers = {}
        for server_id, cfg in (raw.get("servers") or {}).items():
            tools = [
                MCPToolSpec(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("input_schema", {}),
                    handler=t["handler"],
                )
                for t in cfg.get("tools", [])
            ]
            servers[server_id] = MCPServerSpec(
                id=server_id,
                mode=cfg.get("mode", "simulated"),
                description=cfg.get("description", ""),
                base_url=cfg.get("base_url", ""),
                auth_env_var=cfg.get("auth_env_var", ""),
                timeout_seconds=float(cfg.get("timeout_seconds", 5)),
                max_retries=int(cfg.get("max_retries", 1)),
                tools=tools,
            )
        self.servers = servers

    def all_tools(self) -> list[tuple[MCPServerSpec, MCPToolSpec]]:
        return [(server, tool) for server in self.servers.values() for tool in server.tools]

    def find_tool(self, tool_name: str) -> tuple[MCPServerSpec, MCPToolSpec] | None:
        for server, tool in self.all_tools():
            if tool.name == tool_name:
                return server, tool
        return None

    def mark_health(self, server_id: str, healthy: bool, error: str | None = None) -> None:
        server = self.servers.get(server_id)
        if not server:
            return
        server.status = "healthy" if healthy else "unhealthy"
        server.last_checked_at = time.time()
        server.last_error = error

    def as_listing(self) -> list[dict]:
        """Shape returned by GET /mcp/tools."""
        return [
            {
                "server_id": server.id,
                "mode": server.mode,
                "description": server.description,
                "status": server.status,
                "tools": [
                    {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                    for t in server.tools
                ],
            }
            for server in self.servers.values()
        ]


_registry: MCPRegistry | None = None


def get_registry() -> MCPRegistry:
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry