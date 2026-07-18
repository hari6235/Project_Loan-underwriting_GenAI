# FILE: tests/test_prompt_versioning.py
"""Tests for YAML-based prompt version control (Section 3.4, Week 8)."""
import os
import shutil
import tempfile

import pytest
import yaml

from prompt_manager.loader import PromptLoader, load_prompt_file
from prompt_manager.registry import PromptRegistry, PromptNotFoundError
from prompt_manager.validator import validate_raw_prompt_file, PromptValidationError


@pytest.fixture
def tmp_prompts_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _write_prompt(dir_path, filename, raw):
    with open(os.path.join(dir_path, filename), "w") as f:
        yaml.safe_dump(raw, f)


VALID_RAW = {
    "name": "test_prompt",
    "active_version": "1.0.0",
    "versions": [
        {
            "version": "1.0.0",
            "author": "tester",
            "changelog": "initial",
            "model_compatibility": ["gpt-4o-mini"],
            "input_variables": ["question"],
            "template": "Answer this: {question}",
        }
    ],
}


class TestValidator:
    def test_valid_file_passes(self):
        validate_raw_prompt_file(VALID_RAW)  # should not raise

    def test_missing_name_raises(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "name"}
        with pytest.raises(PromptValidationError):
            validate_raw_prompt_file(raw)

    def test_missing_active_version_raises(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "active_version"}
        with pytest.raises(PromptValidationError):
            validate_raw_prompt_file(raw)

    def test_active_version_not_in_versions_raises(self):
        raw = dict(VALID_RAW, active_version="9.9.9")
        with pytest.raises(PromptValidationError):
            validate_raw_prompt_file(raw)

    def test_undeclared_template_variable_raises(self):
        raw = {**VALID_RAW, "versions": [{**VALID_RAW["versions"][0], "template": "Answer {question} using {mystery}"}]}
        with pytest.raises(PromptValidationError):
            validate_raw_prompt_file(raw)

    def test_unused_declared_variable_raises(self):
        raw = {**VALID_RAW, "versions": [{**VALID_RAW["versions"][0], "input_variables": ["question", "unused"]}]}
        with pytest.raises(PromptValidationError):
            validate_raw_prompt_file(raw)

    def test_duplicate_version_raises(self):
        v = VALID_RAW["versions"][0]
        raw = {**VALID_RAW, "versions": [v, v]}
        with pytest.raises(PromptValidationError):
            validate_raw_prompt_file(raw)

    def test_missing_required_field_raises(self):
        v = dict(VALID_RAW["versions"][0])
        del v["changelog"]
        raw = {**VALID_RAW, "versions": [v]}
        with pytest.raises(PromptValidationError):
            validate_raw_prompt_file(raw)


class TestLoader:
    def test_loads_valid_prompt_file(self, tmp_prompts_dir):
        _write_prompt(tmp_prompts_dir, "test_prompt.yaml", VALID_RAW)
        loader = PromptLoader(prompts_dir=tmp_prompts_dir)
        assert "test_prompt" in loader.templates
        assert loader.templates["test_prompt"].active_version == "1.0.0"

    def test_invalid_file_is_skipped_not_fatal(self, tmp_prompts_dir):
        _write_prompt(tmp_prompts_dir, "good.yaml", VALID_RAW)
        _write_prompt(tmp_prompts_dir, "bad.yaml", {"name": "bad"})  # missing required fields
        loader = PromptLoader(prompts_dir=tmp_prompts_dir)
        assert "test_prompt" in loader.templates
        assert "bad" not in loader.templates

    def test_render_fills_template(self, tmp_prompts_dir):
        _write_prompt(tmp_prompts_dir, "test_prompt.yaml", VALID_RAW)
        loader = PromptLoader(prompts_dir=tmp_prompts_dir)
        active = loader.templates["test_prompt"].get_active()
        assert active.render(question="What is DTI?") == "Answer this: What is DTI?"

    def test_render_missing_variable_raises(self, tmp_prompts_dir):
        _write_prompt(tmp_prompts_dir, "test_prompt.yaml", VALID_RAW)
        loader = PromptLoader(prompts_dir=tmp_prompts_dir)
        active = loader.templates["test_prompt"].get_active()
        with pytest.raises(ValueError):
            active.render()


class TestRegistry:
    def test_list_prompts_includes_real_repo_prompts(self):
        registry = PromptRegistry(PromptLoader(prompts_dir="prompts"))
        names = {p["name"] for p in registry.list_prompts()}
        assert {"agent_system", "hitl_review", "rag_qa_chain"}.issubset(names)

    def test_history_marks_active_version(self):
        registry = PromptRegistry(PromptLoader(prompts_dir="prompts"))
        history = registry.history("rag_qa_chain")
        active_entries = [h for h in history if h["is_active"]]
        assert len(active_entries) == 1
        assert active_entries[0]["version"] == "2.1.0"

    def test_get_unknown_prompt_raises(self):
        registry = PromptRegistry(PromptLoader(prompts_dir="prompts"))
        with pytest.raises(PromptNotFoundError):
            registry.get_active("does_not_exist")

    def test_activate_rollback_persists_and_reverts(self, tmp_prompts_dir):
        raw = dict(VALID_RAW)
        raw["versions"] = raw["versions"] + [{
            "version": "2.0.0", "author": "tester", "changelog": "v2",
            "model_compatibility": ["gpt-4o-mini"], "input_variables": ["question"],
            "template": "V2 answer: {question}",
        }]
        raw["active_version"] = "2.0.0"
        _write_prompt(tmp_prompts_dir, "test_prompt.yaml", raw)

        registry = PromptRegistry(PromptLoader(prompts_dir=tmp_prompts_dir))
        assert registry.get_active("test_prompt").version == "2.0.0"

        registry.activate("test_prompt", "1.0.0")
        assert registry.get_active("test_prompt").version == "1.0.0"

        # Persisted to disk, not just in-memory:
        with open(os.path.join(tmp_prompts_dir, "test_prompt.yaml")) as f:
            on_disk = yaml.safe_load(f)
        assert on_disk["active_version"] == "1.0.0"

    def test_activate_unknown_version_raises(self, tmp_prompts_dir):
        _write_prompt(tmp_prompts_dir, "test_prompt.yaml", VALID_RAW)
        registry = PromptRegistry(PromptLoader(prompts_dir=tmp_prompts_dir))
        with pytest.raises(KeyError):
            registry.activate("test_prompt", "99.0.0")


def test_no_hardcoded_prompt_strings_survive_in_python_files():
    """Regression guard for the 'hardcoded prompts surviving migration'
    pitfall: no .py file outside prompt_manager/ itself should define a
    multi-line SYSTEM_PROMPT-style string constant. This is a coarse
    heuristic (not a full AST check) but catches the exact anti-pattern
    this project already had once (prompts/templates.py, now deleted)."""
    import glob
    suspicious = []
    for path in glob.glob("**/*.py", recursive=True):
        if "prompt_manager" in path or "tests" in path or "__pycache__" in path:
            continue
        with open(path, "r", errors="ignore") as f:
            content = f.read()
        if "SYSTEM_PROMPT = \"\"\"" in content or "SYSTEM_PROMPT = (" in content:
            suspicious.append(path)
    assert suspicious == [], f"Hardcoded prompt string constants found in: {suspicious}"