from dataclasses import dataclass, field
from typing import Any


@dataclass
class Subagent:
    id: str
    name: str
    role: str
    model: str
    tools: list[str] = field(default_factory=list)
    kb_inject: list[str] = field(default_factory=list)
    prompt: str = ""
    max_iter: int = 10
    system_addon: str = ""


@dataclass
class SubagentTask:
    agent_id: str
    input: str
    context: dict[str, Any] = field(default_factory=dict)
    artifacts_required: list[str] = field(default_factory=list)
    pipeline_id: str = ""
    stage_id: str = ""
    max_iter: int | None = None


@dataclass
class SubagentResult:
    success: bool
    output: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    cost_usd: float = 0.0
    error: str | None = None
