from pathlib import Path

import pytest

from sdlc.profile.detector import ProfileDetector
from sdlc.profile.models import BUILTIN_PROFILES, ProfileDef
from sdlc.profile.registry import ProfileNotFoundError, ProfileRegistry, register_builtins
from sdlc.utils.yaml_io import save_yaml


def test_profile_def_creation():
    p = ProfileDef(id="test", name="Test")
    assert p.id == "test"
    assert p.name == "Test"
    assert p.entry_kinds == []
    assert p.base_stages == []
    assert p.skip_stages == []
    assert p.extra_stages == []
    assert p.gates == []
    assert p.subagent_overrides == {}
    assert p.severity == "P2"


def test_builtin_profiles_count():
    assert len(BUILTIN_PROFILES) == 14


def test_registry_register_and_get():
    reg = ProfileRegistry()
    p = ProfileDef(id="x", name="X")
    reg.register(p)
    assert reg.get("x") is p


def test_registry_get_not_found():
    reg = ProfileRegistry()
    with pytest.raises(ProfileNotFoundError):
        reg.get("nonexistent")


def test_registry_list_profiles():
    reg = ProfileRegistry()
    p1 = ProfileDef(id="a", name="A")
    p2 = ProfileDef(id="b", name="B")
    reg.register(p1)
    reg.register(p2)
    result = reg.list_profiles()
    assert len(result) == 2
    assert set(r.id for r in result) == {"a", "b"}


def test_registry_has():
    reg = ProfileRegistry()
    assert not reg.has("x")
    reg.register(ProfileDef(id="x"))
    assert reg.has("x")


def test_register_builtins():
    reg = ProfileRegistry()
    count = register_builtins(reg)
    assert count == 14
    assert reg.has("new-feature")
    assert reg.has("bug-fix")
    assert reg.has("hotfix")


def test_resolve_feature():
    reg = ProfileRegistry()
    register_builtins(reg)
    p = reg.resolve("feature")
    assert p.id == "new-feature"


def test_resolve_bug():
    reg = ProfileRegistry()
    register_builtins(reg)
    p = reg.resolve("bug")
    assert p.id == "bug-fix"


def test_resolve_hotfix():
    reg = ProfileRegistry()
    register_builtins(reg)
    p = reg.resolve("hotfix")
    assert p.id == "hotfix"


def test_resolve_refactor():
    reg = ProfileRegistry()
    register_builtins(reg)
    p = reg.resolve("refactor")
    assert p.id == "refactor"


def test_resolve_test():
    reg = ProfileRegistry()
    register_builtins(reg)
    p = reg.resolve("test")
    assert p.id == "test"


def test_resolve_unknown_fallback():
    reg = ProfileRegistry()
    register_builtins(reg)
    p = reg.resolve("unknown-kind")
    assert p.id == "new-feature"


def test_load_from_yaml_single(tmp_path: Path):
    reg = ProfileRegistry()
    data = {
        "id": "custom",
        "name": "Custom",
        "entry_kinds": ["custom"],
        "base_stages": ["s-clarify"],
        "severity": "P2",
    }
    p = tmp_path / "profile.yaml"
    save_yaml(p, data)
    count = reg.load_from_yaml(p)
    assert count == 1
    assert reg.has("custom")
    assert reg.get("custom").name == "Custom"


def test_load_from_yaml_list(tmp_path: Path):
    reg = ProfileRegistry()
    data = {
        "profiles": [
            {"id": "a", "name": "A", "entry_kinds": ["a"], "base_stages": ["s-clarify"]},
            {"id": "b", "name": "B", "entry_kinds": ["b"], "base_stages": ["s-clarify"]},
        ]
    }
    p = tmp_path / "profiles.yaml"
    save_yaml(p, data)
    count = reg.load_from_yaml(p)
    assert count == 2
    assert reg.has("a")
    assert reg.has("b")


def test_detector_detect_feature():
    reg = ProfileRegistry()
    register_builtins(reg)
    det = ProfileDetector(reg)
    p = det.detect("feature")
    assert p.id == "new-feature"


def test_detector_detect_bug():
    reg = ProfileRegistry()
    register_builtins(reg)
    det = ProfileDetector(reg)
    p = det.detect("bug")
    assert p.id == "bug-fix"
