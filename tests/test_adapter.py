
import pytest

from sdlc.adapter.detector import AdapterDetector
from sdlc.adapter.dongboot import DONGBOOT_ADAPTER, register_dongboot
from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterNotFoundError, AdapterRegistry
from sdlc.utils.yaml_io import save_yaml


class TestComponentDef:
    def test_create(self):
        c = ComponentDef(id="c1", type="db", detect="MyDB", enforce=True)
        assert c.id == "c1"
        assert c.type == "db"
        assert c.detect == "MyDB"
        assert c.enforce is True

    def test_defaults(self):
        c = ComponentDef(id="c2", type="cache")
        assert c.detect == ""
        assert c.enforce is True


class TestAdapterDef:
    def test_create(self):
        a = AdapterDef(
            id="test",
            name="Test Adapter",
            detect_patterns=[{"glob": "**/pom.xml", "contains": "test"}],
            components=[ComponentDef(id="c1", type="db")],
        )
        assert a.id == "test"
        assert a.name == "Test Adapter"
        assert len(a.detect_patterns) == 1
        assert len(a.components) == 1

    def test_defaults(self):
        a = AdapterDef(id="x", name="X")
        assert a.version == "1.0"
        assert a.detect_patterns == []
        assert a.components == []
        assert a.enforce_rules is True
        assert a.rule_sets == []
        assert a.required_kb == []


class TestAdapterRegistry:
    def test_register_and_get(self):
        r = AdapterRegistry()
        a = AdapterDef(id="a1", name="A1")
        r.register(a)
        assert r.get("a1") is a

    def test_get_not_found_raises(self):
        r = AdapterRegistry()
        with pytest.raises(AdapterNotFoundError):
            r.get("missing")

    def test_list_adapters(self):
        r = AdapterRegistry()
        a1 = AdapterDef(id="a1", name="A1")
        a2 = AdapterDef(id="a2", name="A2")
        r.register(a1)
        r.register(a2)
        listed = r.list_adapters()
        assert len(listed) == 2
        assert a1 in listed
        assert a2 in listed

    def test_has(self):
        r = AdapterRegistry()
        r.register(AdapterDef(id="x", name="X"))
        assert r.has("x") is True
        assert r.has("y") is False

    def test_load_from_yaml_single(self, tmp_dir):
        r = AdapterRegistry()
        data = {
            "id": "spring",
            "name": "Spring Boot",
            "version": "2.0",
            "detect_patterns": [{"glob": "**/pom.xml", "contains": "spring-boot"}],
            "components": [{"id": "sc", "type": "config", "detect": "@SpringConfig"}],
        }
        p = tmp_dir / "adapter.yml"
        save_yaml(p, data)
        count = r.load_from_yaml(p)
        assert count == 1
        assert r.has("spring")
        a = r.get("spring")
        assert a.name == "Spring Boot"
        assert len(a.components) == 1
        assert a.components[0].id == "sc"

    def test_load_from_yaml_list(self, tmp_dir):
        r = AdapterRegistry()
        data = {
            "adapters": [
                {"id": "a1", "name": "A1"},
                {"id": "a2", "name": "A2"},
            ]
        }
        p = tmp_dir / "adapters.yml"
        save_yaml(p, data)
        count = r.load_from_yaml(p)
        assert count == 2
        assert r.has("a1")
        assert r.has("a2")


class TestDongBoot:
    def test_register_dongboot(self):
        r = AdapterRegistry()
        register_dongboot(r)
        assert r.has("dongboot")
        assert r.get("dongboot") is DONGBOOT_ADAPTER

    def test_has_8_components(self):
        assert len(DONGBOOT_ADAPTER.components) == 8

    def test_has_3_detect_patterns(self):
        assert len(DONGBOOT_ADAPTER.detect_patterns) == 3


class TestAdapterDetector:
    def test_detect_empty_dir(self, tmp_dir):
        r = AdapterRegistry()
        register_dongboot(r)
        d = AdapterDetector(r)
        result = d.detect(tmp_dir)
        assert result == []

    def test_detect_matching_pom(self, tmp_dir):
        r = AdapterRegistry()
        register_dongboot(r)
        d = AdapterDetector(r)
        (tmp_dir / "pom.xml").write_text(
            "<artifactId>dong-boot-starter</artifactId>", encoding="utf-8"
        )
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "dongboot"

    def test_detect_no_match(self, tmp_dir):
        r = AdapterRegistry()
        register_dongboot(r)
        d = AdapterDetector(r)
        (tmp_dir / "pom.xml").write_text("<artifactId>other-lib</artifactId>", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert result == []

    def test_pattern_matches_glob_only(self, tmp_dir):
        r = AdapterRegistry()
        r.register(
            AdapterDef(
                id="plain",
                name="Plain",
                detect_patterns=[{"glob": "**/marker.txt"}],
            )
        )
        d = AdapterDetector(r)
        (tmp_dir / "marker.txt").write_text("hello", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "plain"

    def test_pattern_matches_glob_no_match(self, tmp_dir):
        r = AdapterRegistry()
        r.register(
            AdapterDef(
                id="plain",
                name="Plain",
                detect_patterns=[{"glob": "**/nonexistent.txt"}],
            )
        )
        d = AdapterDetector(r)
        result = d.detect(tmp_dir)
        assert result == []
