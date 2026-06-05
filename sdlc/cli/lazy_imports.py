"""Lazy import helpers for faster CLI startup."""

import importlib
from typing import Any


class LazyImport:
    """Deferred import that only loads the module on first attribute access."""

    def __init__(self, module_name: str):
        self._module_name = module_name
        self._module: Any = None

    def _load(self) -> Any:
        if self._module is None:
            self._module = importlib.import_module(self._module_name)
        return self._module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)

    def __repr__(self) -> str:
        return f"LazyImport({self._module_name!r})"


# Lazy aliases for heavy modules -- actual import deferred until first use.
state_store = LazyImport("sdlc.state")
llm_cache = LazyImport("sdlc.llm.cache")
kb_scanner = LazyImport("sdlc.kb.scanner")
stage_catalog = LazyImport("sdlc.stage.catalog")
stage_runner = LazyImport("sdlc.stage.runner")
rule_engine = LazyImport("sdlc.rule.engine")
