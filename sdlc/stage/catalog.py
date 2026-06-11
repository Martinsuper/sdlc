from __future__ import annotations

import logging
from pathlib import Path

from sdlc.stage.models import StageDef
from sdlc.utils.exceptions import SdlcError
from sdlc.utils.yaml_io import load_yaml

logger = logging.getLogger(__name__)


class StageNotFoundError(SdlcError):
    pass


def _builtin_stages_dir() -> Path:
    """Return the path to sdlc/builtin/stages/."""
    return Path(__file__).resolve().parent.parent / "builtin" / "stages"


class StageCatalog:
    def __init__(self) -> None:
        self._stages: dict[str, StageDef] = {}
        self.load_builtin()

    def register(self, stage_def: StageDef) -> None:
        if stage_def.id in self._stages:
            logger.warning(
                "Stage '%s' already registered; overriding with new definition",
                stage_def.id,
            )
        self._stages[stage_def.id] = stage_def

    def get(self, stage_id: str) -> StageDef:
        stage = self._stages.get(stage_id)
        if not stage:
            raise StageNotFoundError(f"Stage '{stage_id}' not found in catalog")
        return stage

    def list_stages(self) -> list[StageDef]:
        return list(self._stages.values())

    def has(self, stage_id: str) -> bool:
        return stage_id in self._stages

    def for_category(self, category: str) -> list[StageDef]:
        return [s for s in self._stages.values() if s.category == category]

    def load_from_yaml_file(self, path: Path) -> StageDef | None:
        """Load a single stage definition from a YAML file (one stage per file)."""
        data = load_yaml(path)
        if not data or not isinstance(data, dict):
            return None
        stage_id = data.get("id", "")
        if not stage_id:
            logger.warning("Skipping stage in %s: missing 'id' field", path)
            return None
        retry = data.get("retry", {})
        stage = StageDef(
            id=stage_id,
            name=data.get("name", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            subagent=data.get("subagent", ""),
            model=data.get("model", "claude-sonnet-4-20250514"),
            required_artifacts=data.get("required_artifacts", []),
            produces_artifacts=data.get("produces_artifacts", []),
            pre_kb_load=data.get("pre_kb_load", []),
            post_kb_update=data.get("post_kb_update", []),
            timeout=data.get("timeout", 1800),
            max_retries=retry.get("max", 2) if isinstance(retry, dict) else data.get("max_retries", 2),
            retry_backoff=retry.get("backoff", "exponential") if isinstance(retry, dict) else data.get("retry_backoff", "exponential"),
            gates=data.get("gates", []),
        )
        self.register(stage)
        return stage

    def load_builtin(self) -> int:
        """Load all builtin stage YAML files from sdlc/builtin/stages/."""
        stages_dir = _builtin_stages_dir()
        if not stages_dir.is_dir():
            return 0
        count = 0
        for yaml_file in sorted(stages_dir.glob("*.yaml")):
            result = self.load_from_yaml_file(yaml_file)
            if result is not None:
                count += 1
        return count

    def load_from_yaml(self, path: Path) -> int:
        data = load_yaml(path)
        if not data or not isinstance(data, dict):
            return 0
        stages_data = data.get("stages", [])
        if not isinstance(stages_data, list):
            return 0
        count = 0
        for item in stages_data:
            if not isinstance(item, dict):
                continue
            stage = StageDef(
                id=item.get("id", ""),
                name=item.get("name", ""),
                category=item.get("category", ""),
                description=item.get("description", ""),
                subagent=item.get("subagent", ""),
                model=item.get("model", "claude-sonnet-4-20250514"),
                required_artifacts=item.get("required_artifacts", []),
                produces_artifacts=item.get("produces_artifacts", []),
                pre_kb_load=item.get("pre_kb_load", []),
                post_kb_update=item.get("post_kb_update", []),
                timeout=item.get("timeout", 1800),
                max_retries=item.get("max_retries", 2),
                retry_backoff=item.get("retry_backoff", "exponential"),
                gates=item.get("gates", []),
            )
            if stage.id:
                self.register(stage)
                count += 1
            else:
                logger.warning(
                    "Skipping stage entry in %s: missing 'id' field (name=%s)",
                    path,
                    item.get("name", "<unknown>"),
                )
        return count
