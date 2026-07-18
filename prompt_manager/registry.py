# FILE: prompt_manager/registry.py
"""Public interface used by the rest of the app (chains, API routes) to
read the active prompt and manage versions. activate() rewrites
active_version in the source YAML file so a rollback survives a restart --
not just an in-memory pointer -- which is what /prompts/{name}/activate
needs to satisfy "rollback support"."""
from __future__ import annotations

import yaml

from prompt_manager.loader import PromptLoader, get_loader
from prompt_manager.models import PromptTemplate, PromptVersion


class PromptNotFoundError(Exception):
    pass


class PromptRegistry:
    def __init__(self, loader: PromptLoader | None = None):
        self.loader = loader or get_loader()

    def list_prompts(self) -> list[dict]:
        return [
            {
                "name": tpl.name,
                "active_version": tpl.active_version,
                "versions": [v.version for v in tpl.sorted_versions()],
            }
            for tpl in self.loader.templates.values()
        ]

    def get_active(self, name: str) -> PromptVersion:
        tpl = self._get_template(name)
        return tpl.get_active()

    def history(self, name: str) -> list[dict]:
        tpl = self._get_template(name)
        return [
            {
                "version": v.version,
                "author": v.author,
                "changelog": v.changelog,
                "model_compatibility": v.model_compatibility,
                "input_variables": v.input_variables,
                "created_at": v.created_at,
                "is_active": v.version == tpl.active_version,
            }
            for v in tpl.sorted_versions()
        ]

    def activate(self, name: str, version: str) -> dict:
        """Rolls the named prompt forward/back to `version`, persisting the
        change to its YAML file (so it survives a restart) and reloading
        the in-memory copy. Raises PromptNotFoundError / KeyError if the
        name/version don't exist -- callers must not silently no-op."""
        tpl = self._get_template(name)
        if version not in tpl.versions:
            raise KeyError(f"Prompt '{name}' has no version '{version}'")

        with open(tpl.source_path, "r") as f:
            raw = yaml.safe_load(f)
        raw["active_version"] = version
        with open(tpl.source_path, "w") as f:
            yaml.safe_dump(raw, f, sort_keys=False, allow_unicode=True)

        self.loader.reload_one(name)
        return {"name": name, "active_version": version}

    def _get_template(self, name: str) -> PromptTemplate:
        tpl = self.loader.templates.get(name)
        if tpl is None:
            raise PromptNotFoundError(f"No prompt template named '{name}'")
        return tpl


_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry