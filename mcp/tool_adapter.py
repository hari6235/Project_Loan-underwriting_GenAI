# FILE: mcp/tool_adapter.py
"""Translates every registered MCP tool into a LangChain-compatible tool
so the agent (chains/tool_chain.py) treats MCP tools identically to local
deterministic tools -- it selects them purely based on query context, with
no special-casing anywhere in the agent loop."""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from mcp.client import get_client, MCPInvocationError
from mcp.registry import get_registry, MCPToolSpec
from utils.logger import get_logger

logger = get_logger("mcp.tool_adapter")

_JSON_TYPE_MAP = {"string": str, "number": float, "integer": int, "boolean": bool}


def _field_description(spec: dict) -> str:
    parts = []
    if spec.get("description"):
        parts.append(str(spec["description"]))
    if spec.get("enum"):
        parts.append(f"Must be one of: {', '.join(str(v) for v in spec['enum'])}.")
    return " ".join(parts)


def _build_args_schema(tool_name: str, input_schema: dict) -> type[BaseModel]:
    fields = {}
    for field_name, spec in (input_schema or {}).items():
        py_type = _JSON_TYPE_MAP.get(spec.get("type", "string"), str)
        required = bool(spec.get("required"))
        description = _field_description(spec)
        if required:
            field_info = Field(..., description=description) if description else Field(...)
            fields[field_name] = (py_type, field_info)
        else:
            field_info = Field(default=None, description=description) if description else Field(default=None)
            fields[field_name] = (py_type | None, field_info)
    model_name = "".join(part.title() for part in tool_name.split("_")) + "Args"
    return create_model(model_name, **fields)


def _make_runner(tool_name: str):
    def _run(**kwargs) -> dict:
        try:
            result = get_client().invoke(tool_name, kwargs)
            return result["result"]
        except MCPInvocationError as exc:
            logger.warning("MCP tool '%s' invocation failed: %s", tool_name, exc)
            return {"error": str(exc)}
    return _run


def build_mcp_tools() -> list[StructuredTool]:
    """Returns every MCP-registered tool wrapped as a LangChain
    StructuredTool, ready to be included alongside local tools in
    bind_tools()."""
    registry = get_registry()
    tools: list[StructuredTool] = []
    for server, spec in registry.all_tools():
        args_schema = _build_args_schema(spec.name, spec.input_schema)
        tools.append(
            StructuredTool.from_function(
                func=_make_runner(spec.name),
                name=spec.name,
                description=f"[MCP:{server.id}] {spec.description.strip()}",
                args_schema=args_schema,
            )
        )
    logger.info("Built %d MCP-backed LangChain tools from %d servers", len(tools), len(registry.servers))
    return tools