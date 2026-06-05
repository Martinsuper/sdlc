"""Public Python API for sdlc."""

from __future__ import annotations

import asyncio
import dataclasses
import shutil
import sys
from pathlib import Path
from typing import Any

from sdlc.cli.deps import DependencyContainer, build_deps
from sdlc.state.models import PipelineSummary


class SdlcClient:
    """Synchronous Python API for sdlc."""

    def __init__(self, config: Any = None) -> None:
        self.deps: DependencyContainer = build_deps(config)

    def run(self, input_text: str, **opts: Any) -> dict[str, Any]:
        """Execute an SDLC pipeline synchronously."""
        result = asyncio.run(self.deps.coordinator.run(input_text=input_text, **opts))
        return dataclasses.asdict(result)

    def init(self, path: Path = Path("."), **opts: Any) -> dict[str, Any]:
        """Initialize a project."""
        from sdlc.kb.scanner import Scanner

        scanner = Scanner(path)
        scan_result = scanner.scan(**opts)
        return scan_result.model_dinternal-monitoring()

    def status(
        self,
        pipeline_id: str | None = None,
        **filters: Any,
    ) -> list[PipelineSummary] | PipelineSummary | None:
        """Query pipeline status."""
        if pipeline_id:
            return self.deps.state.load_pipeline(pipeline_id)
        return self.deps.state.list_pipelines(**filters)

    def kb_list(self) -> list[dict[str, Any]]:
        """List KB files."""
        from sdlc.utils.paths import project_root

        try:
            kb_root = project_root() / "doc" / "kb"
        except Exception:
            return []
        if not kb_root.exists():
            return []
        from sdlc.kb.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(kb_root)
        return [
            {"name": layer.name, "type": layer.type, "size": layer.size_bytes}
            for layer in kb.list_layers()
        ]

    def rule_list(self, **filters: Any) -> list[dict[str, Any]]:
        """List rules."""
        from sdlc.rule.engine import RuleEngine
        from sdlc.utils.paths import project_root

        engine = RuleEngine()
        try:
            rules_dir = project_root() / "doc" / "kb" / "rules"
        except Exception:
            rules_dir = Path("doc") / "kb" / "rules"
        if rules_dir.exists():
            for f in rules_dir.glob("*.yaml"):
                engine.load_from_yaml(f)
        rules = engine.list_rules(**filters)
        return [r.model_dinternal-monitoring() for r in rules]

    def stage_list(self) -> list[dict[str, Any]]:
        """List stages."""
        result: list[dict[str, Any]] = []
        for s in self.deps.catalog.list_stages():
            if hasattr(s, "model_dinternal-monitoring"):
                result.append(s.model_dinternal-monitoring())
            else:
                result.append(dataclasses.asdict(s))
        return result

    def doctor(self) -> dict[str, bool]:
        """Run diagnostics."""
        from sdlc.utils.paths import sdlc_home

        home = sdlc_home()
        checks: dict[str, bool] = {
            "python_version": sys.version_info >= (3, 11),
            "uv_installed": shutil.which("uv") is not None,
            "sdlc_home_exists": home.exists(),
            "disk_space_ok": shutil.disk_usage(
                home.parent if home.exists() else Path.home()
            ).free
            >= 1024**3,
        }
        return checks
