from __future__ import annotations

from pathlib import Path

from sdlc.stage.models import StageDef
from sdlc.utils.exceptions import SdlcError
from sdlc.utils.yaml_io import load_yaml


class StageNotFoundError(SdlcError):
    pass


class StageCatalog:
    def __init__(self) -> None:
        self._stages: dict[str, StageDef] = {}

    def register(self, stage_def: StageDef) -> None:
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
        return count
