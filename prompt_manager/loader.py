# FILE: prompt_manager/loader.py
"""Loads every *.yaml file in prompts/ into PromptTemplate objects at
startup, validating structure first (prompt_manager/validator.py). Supports
both a manual reload() (called by /prompts/{name}/activate after writing a
rollback) and file-watcher hot-reload via watchdog, so an operator can edit
a YAML directly and have it picked up without restarting the process."""
from __future__ import annotations

import glob
import os

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from prompt_manager.models import PromptTemplate, PromptVersion
from prompt_manager.validator import validate_raw_prompt_file
from utils.logger import get_logger

logger = get_logger("prompt_manager.loader")

DEFAULT_PROMPTS_DIR = "prompts"


def load_prompt_file(path: str) -> PromptTemplate:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    validate_raw_prompt_file(raw, source_path=path)

    versions = {
        v["version"]: PromptVersion(
            version=v["version"],
            author=v["author"],
            changelog=v["changelog"],
            model_compatibility=v["model_compatibility"],
            input_variables=v["input_variables"],
            template=v["template"],
            created_at=v.get("created_at"),
        )
        for v in raw["versions"]
    }
    return PromptTemplate(
        name=raw["name"],
        active_version=raw["active_version"],
        versions=versions,
        source_path=path,
    )


class PromptLoader:
    def __init__(self, prompts_dir: str = DEFAULT_PROMPTS_DIR):
        self.prompts_dir = prompts_dir
        self.templates: dict[str, PromptTemplate] = {}
        self._observer: Observer | None = None
        self.reload_all()

    def reload_all(self) -> None:
        templates = {}
        for path in sorted(glob.glob(os.path.join(self.prompts_dir, "*.yaml"))):
            try:
                tpl = load_prompt_file(path)
                templates[tpl.name] = tpl
            except Exception:
                logger.exception("Failed to load prompt file %s -- keeping previous state for it.", path)
        if templates:
            self.templates = templates
        logger.info("Loaded %d prompt template(s) from %s", len(self.templates), self.prompts_dir)

    def reload_one(self, name: str) -> None:
        tpl = self.templates.get(name)
        if tpl is None or not tpl.source_path:
            return
        self.templates[name] = load_prompt_file(tpl.source_path)

    def start_hot_reload(self) -> None:
        if self._observer is not None:
            return

        loader = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith(".yaml"):
                    logger.info("Detected change in %s -- hot-reloading prompts.", event.src_path)
                    loader.reload_all()

        self._observer = Observer()
        self._observer.schedule(_Handler(), self.prompts_dir, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        logger.info("Prompt hot-reload watcher started on %s", self.prompts_dir)

    def stop_hot_reload(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


_loader: PromptLoader | None = None


def get_loader() -> PromptLoader:
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader