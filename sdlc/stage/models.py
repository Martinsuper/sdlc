from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageDef:
    id: str
    name: str
    category: str
    description: str = ""
    subagent: str = ""
    model: str = "claude-sonnet-4-20250514"
    required_artifacts: list[str] = field(default_factory=list)
    produces_artifacts: list[str] = field(default_factory=list)
    pre_kb_load: list[str] = field(default_factory=list)
    post_kb_update: list[dict[str, str]] = field(default_factory=list)
    timeout: int = 1800
    max_retries: int = 2
    retry_backoff: str = "exponential"
    gates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StageNode:
    id: str
    stage_def: StageDef | None = None
    depends_on: list[str] = field(default_factory=list)
    status: str = "PENDING"
