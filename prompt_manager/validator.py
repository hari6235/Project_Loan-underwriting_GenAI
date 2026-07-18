# FILE: prompt_manager/validator.py
"""Validates a prompt YAML file's structure before it's loaded into the
registry. Catches the exact failure mode the "YAML prompt without
testing" and "hardcoded prompts surviving migration" pitfalls warn about:
malformed metadata, an active_version that doesn't exist, or a template
that references variables not declared in input_variables (which would
KeyError at render time in production instead of at load time)."""
from __future__ import annotations

REQUIRED_VERSION_FIELDS = {"version", "author", "changelog", "model_compatibility", "input_variables", "template"}


class PromptValidationError(Exception):
    pass


def validate_raw_prompt_file(raw: dict, source_path: str = "<unknown>") -> None:
    if "name" not in raw:
        raise PromptValidationError(f"{source_path}: missing top-level 'name'")
    if "active_version" not in raw:
        raise PromptValidationError(f"{source_path}: missing top-level 'active_version'")
    if "versions" not in raw or not isinstance(raw["versions"], list) or not raw["versions"]:
        raise PromptValidationError(f"{source_path}: 'versions' must be a non-empty list")

    seen_versions = set()
    for i, v in enumerate(raw["versions"]):
        missing = REQUIRED_VERSION_FIELDS - set(v or {})
        if missing:
            raise PromptValidationError(
                f"{source_path}: versions[{i}] missing required field(s): {sorted(missing)}"
            )
        if v["version"] in seen_versions:
            raise PromptValidationError(f"{source_path}: duplicate version '{v['version']}'")
        seen_versions.add(v["version"])

        # Every variable the template actually uses must be declared --
        # and vice versa, every declared variable must be used (a stale
        # declared-but-unused variable is a silent drift signal too).
        import re
        referenced = set(re.findall(r"\{(\w+)\}", v["template"]))
        declared = set(v["input_variables"])
        undeclared = referenced - declared
        if undeclared:
            raise PromptValidationError(
                f"{source_path}: version {v['version']} template references undeclared "
                f"variable(s) {sorted(undeclared)} -- add them to input_variables."
            )
        unused = declared - referenced
        if unused:
            raise PromptValidationError(
                f"{source_path}: version {v['version']} declares unused input_variables "
                f"{sorted(unused)} -- remove them or use them in the template."
            )

    if raw["active_version"] not in seen_versions:
        raise PromptValidationError(
            f"{source_path}: active_version '{raw['active_version']}' is not among "
            f"declared versions {sorted(seen_versions)}"
        )