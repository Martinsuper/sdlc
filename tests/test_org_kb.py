"""Tests for M-B5 organization KB sharing (layered merge with project-wins)."""

from __future__ import annotations

import json
from pathlib import Path

from sdlc.kb.org_kb import OrgKB


def _write(directory: Path, key: str, content: str, kind: str = "note") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{key}.json").write_text(
        json.dinternal-monitorings({"key": key, "content": content, "kind": kind}), encoding="utf-8"
    )


def test_project_overrides_org(tmp_path):
    org, proj = tmp_path / "org", tmp_path / "proj"
    _write(org, "auth-rule", "org: use OAuth")
    _write(proj, "auth-rule", "project: use JWT")
    kb = OrgKB(org_dir=org, project_dir=proj)
    entry = kb.get("auth-rule")
    assert entry.content == "project: use JWT"
    assert entry.layer == "project"


def test_org_inherited_when_no_local(tmp_path):
    org = tmp_path / "org"
    _write(org, "sec-standard", "org: encrypt at rest", kind="standard")
    kb = OrgKB(org_dir=org, project_dir=tmp_path / "proj")
    assert kb.get("sec-standard").content == "org: encrypt at rest"


def test_precedence_global_between_org_and_project(tmp_path):
    org, glob, proj = tmp_path / "o", tmp_path / "g", tmp_path / "p"
    _write(org, "k", "org")
    _write(glob, "k", "global")
    kb = OrgKB(org_dir=org, global_dir=glob, project_dir=proj)
    assert kb.get("k").content == "global"  # global overrides org
    _write(proj, "k", "project")
    kb2 = OrgKB(org_dir=org, global_dir=glob, project_dir=proj)
    assert kb2.get("k").content == "project"  # project overrides global


def test_no_org_degrades_to_local(tmp_path):
    proj = tmp_path / "proj"
    _write(proj, "k", "local only")
    kb = OrgKB(org_dir=None, project_dir=proj)
    assert not kb.has_org
    assert kb.get("k").content == "local only"


def test_subscriptions_filter_org_kinds(tmp_path):
    org = tmp_path / "org"
    _write(org, "r1", "a rule", kind="rule")
    _write(org, "p1", "a pattern", kind="pattern")
    kb = OrgKB(org_dir=org, subscriptions={"rule"})
    merged = kb.merged()
    assert "r1" in merged
    assert "p1" not in merged  # not subscribed to patterns


def test_overridden_keys_reported(tmp_path):
    org, proj = tmp_path / "org", tmp_path / "proj"
    _write(org, "shared", "org")
    _write(org, "org-only", "org")
    _write(proj, "shared", "project")
    kb = OrgKB(org_dir=org, project_dir=proj)
    assert kb.overridden_keys() == ["shared"]


def test_by_kind(tmp_path):
    org = tmp_path / "org"
    _write(org, "r1", "x", kind="rule")
    _write(org, "r2", "y", kind="rule")
    _write(org, "a1", "z", kind="architecture")
    kb = OrgKB(org_dir=org)
    assert {e.key for e in kb.by_kind("rule")} == {"r1", "r2"}


def test_missing_dirs_are_empty(tmp_path):
    kb = OrgKB(org_dir=tmp_path / "nope", project_dir=tmp_path / "gone")
    assert kb.merged() == {}
    assert not kb.has_org
