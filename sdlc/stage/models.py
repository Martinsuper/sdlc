from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

_VALID_BACKOFF_STRATEGIES = ("exponential", "linear", "fixed")


class PipelineStatus(StrEnum):
    """Standardized status values for Pipeline and StageNode."""

    NEW = "NEW"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"


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
    # M-A2 Plan-Act-Reflect. Defaults keep every existing stage single-shot;
    # a stage opts in via `runtime: par` + `planning` in its YAML.
    runtime: str = "single"          # single | par
    planning: str = "off"            # off | optional | required
    max_reflect: int = 2
    reflect_model: str = ""          # "" = use the agent's model
    acceptance_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.retry_backoff not in _VALID_BACKOFF_STRATEGIES:
            raise ValueError(
                f"Invalid retry_backoff '{self.retry_backoff}'; "
                f"must be one of {_VALID_BACKOFF_STRATEGIES}"
            )


@dataclass
class StageNode:
    id: str
    stage_def: StageDef | None = None
    depends_on: list[str] = field(default_factory=list)
    status: str = PipelineStatus.PENDING
