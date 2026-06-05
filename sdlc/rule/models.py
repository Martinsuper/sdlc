"""sdlc.rule.models — data models for the rule subsystem."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RuleLevel(StrEnum):
    MUST = "MUST"
    MUST_NOT = "MUST_NOT"
    SHOULD = "SHOULD"
    SHOULD_NOT = "SHOULD_NOT"
    MAY = "MAY"
    MAY_NOT = "MAY_NOT"


class RuleAction(StrEnum):
    BLOCK = "block"
    WARN = "warn"


class Rule(BaseModel):
    """A single rule definition."""

    id: str
    level: RuleLevel = RuleLevel.MUST
    category: str = "coding"
    description: str = ""
    enforcer: str = "cr"
    pattern: str | None = None
    message: str | None = None
    applies_to: list[str] = Field(default_factory=list)
    action: RuleAction = RuleAction.WARN
    severity: str = "P2"
    scope: dict[str, list[str]] = Field(default_factory=dict)
    references: list[str] = Field(default_factory=list)
    auto_generated: bool = False
    disabled: bool = False
    disabled_reason: str | None = None
    disabled_until: str | None = None


class Violation(BaseModel):
    """A rule violation detected during a check."""

    rule_id: str
    file: str | None = None
    line: int | None = None
    message: str
    severity: str = "error"


class RuleException(BaseModel):
    """A temporary exemption for a rule."""

    id: str
    rule_id: str
    reason: str
    granted_by: str
    granted_at: str
    expires_at: str
    scope: dict[str, list[str]] = Field(default_factory=dict)
    auto_renew: bool = False
