# FILE: rbac/role_registry.py
"""Loads config/roles.yaml into Role objects, with a fail-closed default
for any role name not explicitly listed."""
from __future__ import annotations

import yaml

from rbac.models import Role

DEFAULT_ROLES_PATH = "config/roles.yaml"


class RoleRegistry:
    def __init__(self, config_path: str = DEFAULT_ROLES_PATH):
        self.config_path = config_path
        self.roles: dict[str, Role] = {}
        self.default_role: Role = Role(name="__default__", description="fail-closed default")
        self.reload()

    def reload(self) -> None:
        with open(self.config_path, "r") as f:
            raw = yaml.safe_load(f) or {}

        self.roles = {
            name: Role(
                name=name,
                description=cfg.get("description", ""),
                allowed_doc_types=cfg.get("allowed_doc_types", []) or [],
                denied_doc_types=cfg.get("denied_doc_types", []) or [],
                can_request_hitl_override=bool(cfg.get("can_request_hitl_override", False)),
            )
            for name, cfg in (raw.get("roles") or {}).items()
        }

        default_cfg = raw.get("default_role", {}) or {}
        self.default_role = Role(
            name="__default__",
            description="fail-closed default for unrecognised roles",
            allowed_doc_types=default_cfg.get("allowed_doc_types", []) or [],
            denied_doc_types=default_cfg.get("denied_doc_types", []) or [],
            can_request_hitl_override=bool(default_cfg.get("can_request_hitl_override", False)),
        )

    def get(self, role_name: str) -> Role:
        return self.roles.get(role_name, self.default_role)

    def list_roles(self) -> list[dict]:
        return [
            {
                "name": role.name,
                "description": role.description,
                "allowed_doc_types": role.allowed_doc_types,
                "denied_doc_types": role.denied_doc_types,
                "can_request_hitl_override": role.can_request_hitl_override,
            }
            for role in self.roles.values()
        ]


_registry: RoleRegistry | None = None


def get_role_registry() -> RoleRegistry:
    global _registry
    if _registry is None:
        _registry = RoleRegistry()
    return _registry