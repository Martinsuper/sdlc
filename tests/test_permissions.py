"""Tests for M-B6 lightweight permission model (roles + gate approver binding)."""

from __future__ import annotations

from sdlc.gate.models import GateDef
from sdlc.server.auth import Role, RoleRegistry, can_approve, parse_role


def test_parse_role_case_insensitive():
    assert parse_role("Security") == Role.SECURITY
    assert parse_role("PM") == Role.PM


def test_parse_role_unknown_is_none():
    assert parse_role("wizard") is None
    assert parse_role(None) is None


def test_open_gate_allows_anyone():
    g = GateDef(id="g", name="g", after_stage="s1")  # no approver_roles
    assert can_approve(Role.PM, g)
    assert can_approve(None, g)  # personal mode


def test_restricted_gate_requires_matching_role():
    g = GateDef(id="g", name="g", after_stage="s1", approver_roles=["security"])
    assert can_approve(Role.SECURITY, g)
    assert not can_approve(Role.PM, g)


def test_restricted_gate_personal_mode_allowed():
    # role=None (no server / personal mode) is not blocked.
    g = GateDef(id="g", name="g", after_stage="s1", approver_roles=["security"])
    assert can_approve(None, g)


def test_multi_role_gate():
    g = GateDef(id="g", name="g", after_stage="s1", approver_roles=["tl", "sre"])
    assert can_approve(Role.TL, g)
    assert can_approve(Role.SRE, g)
    assert not can_approve(Role.QA, g)


def test_role_registry_binds_token():
    reg = RoleRegistry()
    reg.bind("tok-1", Role.SECURITY)
    assert reg.role_for("tok-1") == Role.SECURITY
    assert reg.role_for("unknown") is None
    assert reg.role_for(None) is None


def test_all_five_roles_exist():
    assert {r.value for r in Role} == {"pm", "tl", "sre", "qa", "security"}
