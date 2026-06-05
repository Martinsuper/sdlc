from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GateAction(StrEnum):
    AUTO_PASS = "auto_pass"
    MANUAL_REVIEW = "manual_review"
    BLOCK = "block"
    ESCALATE = "escalate"


class GateTrigger(StrEnum):
    ALWAYS = "always"
    ON_SEVERITY = "on_severity"
    ON_ARTIFACT = "on_artifact"
    ON_RULE_VIOLATION = "on_rule_violation"
    ON_FAILURE = "on_failure"
    ON_STAGE_END = "on_stage_end"


@dataclass
class GateDef:
    id: str
    name: str
    after_stage: str
    trigger: GateTrigger = GateTrigger.ALWAYS
    reviewer: str = ""
    deadline_hours: int = 4
    severities: list[str] = field(default_factory=list)
    auto_pass_conditions: dict[str, Any] = field(default_factory=dict)
    block_conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateDecision:
    gate_id: str
    action: GateAction
    reason: str = ""
    reviewer: str = ""
    deadline: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
