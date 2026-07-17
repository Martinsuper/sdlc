"""Lightweight permission model (M-B6).

Five built-in roles and a single ``can_approve`` check binding roles to gates.
Deliberately minimal — no fine-grained RBAC matrix, no approval-flow engine, no
field-level permissions (that企业-IAM complexity is out of scope per the design).

Personal mode (no server / no role) bypasses the check entirely, so single-user
CLI use is never blocked by permissions.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sdlc.gate.models import GateDef


class Role(StrEnum):
    PM = "pm"
    TL = "tl"
    SRE = "sre"
    QA = "qa"
    SECURITY = "security"


def parse_role(value: str | None) -> Role | None:
    """Parse a role string case-insensitively; None if unset/unknown."""
    if not value:
        return None
    try:
        return Role(value.lower())
    except ValueError:
        return None


def can_approve(role: Role | None, gate: GateDef) -> bool:
    """Whether *role* may approve *gate*.

    Rules (least privilege, but personal-mode friendly):
      - a gate with no approver_roles is open to anyone (including role=None,
        i.e. personal mode) — permissions only bite where a gate opts in;
      - a gate that names approver_roles requires a matching role; role=None
        (personal mode) is allowed through so single-user CLI is not blocked.
    """
    required = getattr(gate, "approver_roles", None) or []
    if not required:
        return True
    if role is None:
        # Personal mode: no role configured => do not block (server enforces).
        return True
    return role.value in required


class RoleRegistry:
    """Maps auth tokens to roles (server-side). In personal mode this is empty
    and every lookup returns None, so can_approve waves approvals through."""

    def __init__(self) -> None:
        self._token_roles: dict[str, Role] = {}

    def bind(self, token: str, role: Role) -> None:
        self._token_roles[token] = role

    def role_for(self, token: str | None) -> Role | None:
        if not token:
            return None
        return self._token_roles.get(token)
