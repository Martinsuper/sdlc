from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sdlc.profile.models import ProfileDef
from sdlc.stage.models import PipelineStatus, StageNode


class EntryKind(StrEnum):
    IDEA = "idea"
    FEATURE = "feature"
    BUG = "bug"
    HOTFIX = "hotfix"
    REFACTOR = "refactor"
    TEST = "test"
    INFRA = "infra"
    RELEASE = "release"
    REVERT = "revert"
    DOC = "doc"
    MIGRATE = "migrate"
    AUDIT = "audit"


@dataclass
class EntryPoint:
    kind: EntryKind
    raw_input: str
    detected_attachments: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Pipeline:
    id: str
    entry: EntryPoint
    profile: ProfileDef | None = None
    stages: list[StageNode] = field(default_factory=list)
    status: str = PipelineStatus.NEW
    created_at: str = ""
    updated_at: str = ""


@dataclass
class PipelineResult:
    pipeline_id: str
    status: str
    stage_results: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    error: str | None = None
