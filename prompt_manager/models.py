# FILE: prompt_manager/models.py
from __future__ import annotations

import re
from dataclasses import dataclass, field

_TEMPLATE_VAR_RE = re.compile(r"\{(\w+)\}")


@dataclass
class PromptVersion:
    version: str
    author: str
    changelog: str
    model_compatibility: list[str]
    input_variables: list[str]
    template: str
    created_at: str | None = None

    def referenced_variables(self) -> set[str]:
        return set(_TEMPLATE_VAR_RE.findall(self.template))

    def render(self, **kwargs) -> str:
        missing = set(self.input_variables) - set(kwargs)
        if missing:
            raise ValueError(f"Missing template variable(s): {sorted(missing)}")
        return self.template.format(**kwargs)


@dataclass
class PromptTemplate:
    name: str
    active_version: str
    versions: dict[str, PromptVersion] = field(default_factory=dict)
    source_path: str | None = None

    def get_active(self) -> PromptVersion:
        return self.versions[self.active_version]

    def get_version(self, version: str) -> PromptVersion:
        if version not in self.versions:
            raise KeyError(f"Prompt '{self.name}' has no version '{version}'")
        return self.versions[version]

    def sorted_versions(self) -> list[PromptVersion]:
        return [self.versions[v] for v in sorted(self.versions, key=_version_key)]


def _version_key(v: str) -> tuple:
    """Sorts semantic-version strings ('2.10.0' > '2.9.0'), falling back to
    lexicographic if a version string isn't strictly semver."""
    try:
        return tuple(int(p) for p in v.split("."))
    except ValueError:
        return (v,)