"""Tests for sdlc.kb package."""

import hashlib
import json
from pathlib import Path

import pytest

from sdlc.audit import AuditEventType, AuditLogger
from sdlc.kb import (
    KBDeltaResult,
    KBFileNotFoundError,
    KBLayer,
    KBWriter,
    KnowledgeBase,
    Reconciler,
    Scanner,
    ScanResult,
    compute_kb_fingerprint,
    compute_layer_fingerprint,
)
from sdlc.utils.exceptions import KBWriteConflictError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def kb_root(tmp_path: Path) -> Path:
    """Create a minimal KB directory tree."""
    root = tmp_path / "kb"
    arch = root / "architecture"
    arch.mkdir(parents=True)

    (arch / "component-catalog.md").write_text("# Components\n", encoding="utf-8")
    (arch / "deps.yaml").write_text("components:\n  - name: foo\n", encoding="utf-8")
    (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    (root / "meta.json").write_text('{"version": 1}', encoding="utf-8")
    return root


@pytest.fixture()
def kb(kb_root: Path) -> KnowledgeBase:
    return KnowledgeBase(kb_root)


@pytest.fixture()
def audit_log(tmp_path: Path) -> AuditLogger:
    return AuditLogger(tmp_path / "audit.jsonl")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a realistic project directory for scanner tests."""
    root = tmp_path / "myproject"
    root.mkdir()

    pkg = {
        "name": "my-app",
        "dependencies": {"react": "^18.0.0", "express": "^4.18.0"},
        "devDependencies": {"jest": "^29.0.0"},
        "scripts": {"start": "node index.js", "test": "jest"},
    }
    (root / "package.json").write_text(json.dinternal-monitorings(pkg), encoding="utf-8")

    src = root / "src"
    src.mkdir()
    (src / "index.ts").write_text('console.log("hello");', encoding="utf-8")
    (src / "app.py").write_text("print('hello')", encoding="utf-8")

    (root / "README.md").write_text("# My App\n", encoding="utf-8")

    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: CI\n", encoding="utf-8")

    (root / "Dockerfile").write_text("FROM node:18\n", encoding="utf-8")

    (root / ".eslintrc.json").write_text("{}", encoding="utf-8")

    (root / ".prettierrc").write_text("{}", encoding="utf-8")

    husky = root / ".husky"
    husky.mkdir()
    (husky / "pre-commit").write_text("#!/bin/sh\n", encoding="utf-8")

    (root / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")

    docs = root / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")

    adr = docs / "adr"
    adr.mkdir()
    (adr / "001-choice.md").write_text("# ADR 1\n", encoding="utf-8")

    (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

    return root


@pytest.fixture()
def python_project(tmp_path: Path) -> Path:
    """Create a Python project with pyproject.toml and requirements.txt."""
    root = tmp_path / "pyproject"
    root.mkdir()

    pyproject = '''
[project]
name = "my-py-app"
dependencies = [
    "flask>=3.0",
    "requests>=2.31",
]
'''
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (root / "requirements.txt").write_text("flask>=3.0\nrequests>=2.31\ncelery>=5.3\n", encoding="utf-8")
    (root / "main.py").write_text("from flask import Flask\n", encoding="utf-8")
    (root / "app.py").write_text("app = Flask(__name__)\n", encoding="utf-8")
    return root


@pytest.fixture()
def java_project(tmp_path: Path) -> Path:
    """Create a Java project with pom.xml."""
    root = tmp_path / "javaproject"
    root.mkdir()
    pom = """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <dependencies>
    <dependency>
      <artifactId>spring-boot-starter</artifactId>
    </dependency>
    <dependency>
      <artifactId>dong-boot-starter</artifactId>
    </dependency>
  </dependencies>
</project>
"""
    (root / "pom.xml").write_text(pom, encoding="utf-8")
    src = root / "src" / "main" / "java"
    src.mkdir(parents=True)
    (src / "Application.java").write_text("public class Application {}", encoding="utf-8")
    return root


@pytest.fixture()
def go_project(tmp_path: Path) -> Path:
    """Create a Go project with go.mod."""
    root = tmp_path / "goproject"
    root.mkdir()
    gomod = """module github.com/example/myapp

go 1.21

require (
\tgithub.com/gin-gonic/gin v1.9.0
)
"""
    (root / "go.mod").write_text(gomod, encoding="utf-8")
    (root / "main.go").write_text("package main\n", encoding="utf-8")
    return root


# ===========================================================================
# KnowledgeBase tests
# ===========================================================================


class TestKnowledgeBase:
    def test_init_loads_layers(self, kb: KnowledgeBase) -> None:
        assert len(kb.layers) >= 3
        names = set(kb.layers)
        assert "architecture/component-catalog.md" in names
        assert "architecture/deps.yaml" in names
        assert "conventions.md" in names

    def test_init_empty_root(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_kb"
        empty.mkdir()
        kb = KnowledgeBase(empty)
        assert len(kb.layers) == 0

    def test_init_nonexistent_root(self, tmp_path: Path) -> None:
        missing = tmp_path / "no_such_dir"
        kb = KnowledgeBase(missing)
        assert len(kb.layers) == 0

    def test_scope_attribute(self, kb_root: Path) -> None:
        kb = KnowledgeBase(kb_root, scope="global")
        assert kb.scope == "global"

    def test_root_attribute(self, kb: KnowledgeBase, kb_root: Path) -> None:
        assert kb.root == kb_root

    def test_get_existing_layer(self, kb: KnowledgeBase) -> None:
        layer = kb.get("conventions.md")
        assert isinstance(layer, KBLayer)
        assert layer.name == "conventions.md"
        assert layer.type == "markdown"

    def test_get_yaml_layer(self, kb: KnowledgeBase) -> None:
        layer = kb.get("architecture/deps.yaml")
        assert layer.type == "yaml"

    def test_get_json_layer(self, kb: KnowledgeBase) -> None:
        layer = kb.get("meta.json")
        assert layer.type == "json"

    def test_get_missing_raises(self, kb: KnowledgeBase) -> None:
        with pytest.raises(KBFileNotFoundError, match="no-such-file"):
            kb.get("no-such-file")

    def test_list_layers_all(self, kb: KnowledgeBase) -> None:
        all_layers = kb.list_layers()
        assert len(all_layers) >= 3

    def test_list_layers_pattern(self, kb: KnowledgeBase) -> None:
        yaml_layers = kb.list_layers("*.yaml")
        assert len(yaml_layers) == 1
        assert yaml_layers[0].name == "architecture/deps.yaml"

    def test_list_layers_glob_star_star(self, kb: KnowledgeBase) -> None:
        arch = kb.list_layers("architecture/*")
        assert len(arch) >= 2

    def test_exists_true(self, kb: KnowledgeBase) -> None:
        assert kb.exists("conventions.md") is True

    def test_exists_false(self, kb: KnowledgeBase) -> None:
        assert kb.exists("does-not-exist.md") is False

    def test_read_content(self, kb: KnowledgeBase) -> None:
        content = kb.read_content("conventions.md")
        assert "# Conventions" in content

    def test_read_content_missing_raises(self, kb: KnowledgeBase) -> None:
        with pytest.raises(KBFileNotFoundError):
            kb.read_content("ghost.md")

    def test_layer_has_fingerprint(self, kb: KnowledgeBase) -> None:
        layer = kb.get("conventions.md")
        assert layer.fingerprint
        assert len(layer.fingerprint) == 64

    def test_layer_has_size_bytes(self, kb: KnowledgeBase) -> None:
        layer = kb.get("conventions.md")
        assert layer.size_bytes > 0


# ===========================================================================
# KBWriter tests
# ===========================================================================


class TestKBWriter:
    def test_update_after_stage_append_new_file(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        deltas = writer.update_after_stage(
            "s1",
            [{"target": "architecture/new-section.md", "operation": "append", "content": "## New Section\nHello world"}],
        )
        assert len(deltas) == 1
        d = deltas[0]
        assert not d.skipped
        assert d.operation == "append"
        assert d.target == "architecture/new-section.md"
        assert (kb.root / "architecture/new-section.md").is_file()
        content = (kb.root / "architecture/new-section.md").read_text("utf-8")
        assert "Hello world" in content

    def test_update_after_stage_append_existing(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        writer.update_after_stage(
            "s1",
            [{"target": "architecture/component-catalog.md", "operation": "append", "content": "## Appended"}],
        )
        original = (kb.root / "architecture/component-catalog.md").read_text("utf-8")
        assert "## Appended" in original

    def test_fingerprint_dedup(self, kb: KnowledgeBase, audit_log: AuditLogger) -> None:
        writer = KBWriter(kb, audit=audit_log)
        upd = {"target": "architecture/component-catalog.md", "operation": "append", "content": "Dedup content"}
        d1 = writer.update_after_stage("s1", [upd])[0]
        assert not d1.skipped
        d2 = writer.update_after_stage("s2", [upd])[0]
        assert d2.skipped
        assert d2.skip_reason == "duplicate target"

    def test_human_only_file_skipped(self, kb: KnowledgeBase, audit_log: AuditLogger) -> None:
        writer = KBWriter(kb, audit=audit_log)
        deltas = writer.update_after_stage(
            "s1",
            [{"target": "conventions.md", "operation": "append", "content": "Should be skipped"}],
        )
        d = deltas[0]
        assert d.skipped
        assert "human-only" in d.skip_reason

    def test_append_mode_creates_section_header(self, kb: KnowledgeBase) -> None:
        writer = KBWriter(kb)
        writer.update_after_stage(
            "s1",
            [{"target": "architecture/new-section.md", "operation": "append", "content": "Section body"}],
        )
        content = (kb.root / "architecture/new-section.md").read_text("utf-8")
        assert "Auto-generated by SDLC stage" in content

    def test_update_mode_yaml(self, kb: KnowledgeBase, audit_log: AuditLogger) -> None:
        writer = KBWriter(kb, audit=audit_log)
        deltas = writer.update_after_stage(
            "s1",
            [{"target": "architecture/deps.yaml", "operation": "update", "content": '{"new_key": "new_value"}'}],
        )
        d = deltas[0]
        assert not d.skipped
        from sdlc.utils.yaml_io import load_yaml
        data = load_yaml(kb.root / "architecture/deps.yaml")
        assert data["new_key"] == "new_value"

    def test_update_mode_missing_file_raises(self, kb: KnowledgeBase) -> None:
        writer = KBWriter(kb)
        with pytest.raises(KBWriteConflictError, match="Cannot update"):
            writer.update_after_stage("s1", [{"target": "nonexistent.yaml", "operation": "update", "content": "{}"}])

    def test_unknown_operation_raises(self, kb: KnowledgeBase) -> None:
        writer = KBWriter(kb)
        with pytest.raises(KBWriteConflictError, match="Unknown KB write operation"):
            writer.update_after_stage("s1", [{"target": "architecture/new.md", "operation": "delete", "content": "oops"}])

    def test_audit_events_emitted(self, kb: KnowledgeBase, audit_log: AuditLogger) -> None:
        writer = KBWriter(kb, audit=audit_log)
        writer.update_after_stage(
            "s1",
            [{"target": "architecture/new-section.md", "operation": "append", "content": "Audit test"}],
        )
        events = list(audit_log.query(event_type=AuditEventType.KB_UPDATED))
        assert len(events) >= 1
        assert events[0]["payload"]["action"] == "written"

    def test_audit_skip_event(self, kb: KnowledgeBase, audit_log: AuditLogger) -> None:
        writer = KBWriter(kb, audit=audit_log)
        writer.update_after_stage(
            "s1",
            [{"target": "conventions.md", "operation": "append", "content": "Skip audit"}],
        )
        events = list(audit_log.query(event_type=AuditEventType.KB_UPDATED))
        assert len(events) == 1
        assert events[0]["payload"]["action"] == "skip_human_only"

    def test_no_audit_logger_does_not_crash(self, kb: KnowledgeBase) -> None:
        writer = KBWriter(kb, audit=None)
        deltas = writer.update_after_stage(
            "s1",
            [{"target": "architecture/new.md", "operation": "append", "content": "No audit"}],
        )
        assert len(deltas) == 1
        assert not deltas[0].skipped

    def test_idempotent_append(self, kb: KnowledgeBase) -> None:
        writer = KBWriter(kb)
        upd = {"target": "architecture/idem.md", "operation": "append", "content": "Idempotent check"}
        d1 = writer.update_after_stage("s1", [upd])[0]
        assert not d1.skipped
        d2 = writer.update_after_stage("s2", [upd])[0]
        assert d2.skipped

    def test_writer_refreshes_layer(self, kb: KnowledgeBase) -> None:
        writer = KBWriter(kb)
        writer.update_after_stage(
            "s1",
            [{"target": "architecture/new-layer.md", "operation": "append", "content": "Fresh layer"}],
        )
        assert kb.exists("architecture/new-layer.md")
        layer = kb.get("architecture/new-layer.md")
        assert layer.size_bytes > 0


# ===========================================================================
# Fingerprint tests
# ===========================================================================


class TestFingerprint:
    def test_compute_kb_fingerprint(self, tmp_path: Path) -> None:
        content = "hello world"
        p = tmp_path / "test.txt"
        p.write_text(content, encoding="utf-8")
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert compute_kb_fingerprint(p) == expected

    def test_compute_kb_fingerprint_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.txt"
        p.write_bytes(b"")
        assert compute_kb_fingerprint(p) == hashlib.sha256(b"").hexdigest()

    def test_compute_layer_fingerprint(self, tmp_path: Path) -> None:
        p = tmp_path / "test.txt"
        p.write_text("file content", encoding="utf-8")
        expected = hashlib.sha256(b"file content").hexdigest()
        assert compute_layer_fingerprint(p) == expected

    def test_compute_layer_fingerprint_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            compute_layer_fingerprint(tmp_path / "gone.txt")


# ===========================================================================
# Scanner tests
# ===========================================================================


class TestScanner:
    def test_scan_returns_scan_result(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan()
        assert isinstance(result, ScanResult)

    def test_root_stored(self, tmp_path: Path) -> None:
        scanner = Scanner(tmp_path)
        assert scanner.root == tmp_path

    def test_config_defaults_to_empty_dict(self, tmp_path: Path) -> None:
        scanner = Scanner(tmp_path)
        assert scanner.config == {}

    def test_config_custom(self, tmp_path: Path) -> None:
        scanner = Scanner(tmp_path, config={"key": "value"})
        assert scanner.config == {"key": "value"}

    def test_scan_detects_languages(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        meta = json.loads(result.kb_files["meta.json"])
        assert "TypeScript" in meta["languages"] or "Python" in meta["languages"]

    def test_scan_detects_frameworks(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        meta = json.loads(result.kb_files["meta.json"])
        assert "react" in meta["frameworks"] or "express" in meta["frameworks"]

    def test_scan_detects_ci(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        meta = json.loads(result.kb_files["meta.json"])
        assert ".github/workflows" in meta["ci_configs"]

    def test_scan_detects_containers(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        meta = json.loads(result.kb_files["meta.json"])
        assert "Dockerfile" in meta["container_configs"]

    def test_scan_recommends_node_adapter(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        assert "node adapter" in result.recommendations

    def test_scan_recommends_new_feature_profile(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        assert "new-feature profile" in result.recommendations

    def test_scan_generates_kb_files(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        assert "conventions.md" in result.kb_files
        assert "architecture/component-catalog.md" in result.kb_files
        assert "architecture/deps.yaml" in result.kb_files
        assert "architecture/standards.md" in result.kb_files
        assert "architecture/ci.md" in result.kb_files
        assert "meta.json" in result.kb_files

    def test_scan_confidence_positive(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        assert result.confidence > 0.0

    def test_scan_empty_project(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        scanner = Scanner(empty)
        result = scanner.scan(no_llm=True)
        assert isinstance(result, ScanResult)
        assert result.confidence == 0.0
        assert any("No manifest files detected" in w for w in result.warnings) or any("No source files detected" in w for w in result.warnings)

    def test_scan_no_llm_skips_ai(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        assert any("AI analysis skipped" in w for w in result.warnings)

    def test_scan_detects_lint_configs(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        standards = result.kb_files["architecture/standards.md"]
        assert ".eslintrc.json" in standards

    def test_scan_detects_formatter_configs(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        standards = result.kb_files["architecture/standards.md"]
        assert ".prettierrc" in standards

    def test_scan_detects_git_hooks(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        standards = result.kb_files["architecture/standards.md"]
        assert ".husky" in standards

    def test_scan_detects_existing_docs(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        assert isinstance(result, ScanResult)

    def test_scan_detects_existing_kb(self, tmp_path: Path) -> None:
        root = tmp_path / "withkb"
        root.mkdir()
        kb_dir = root / "doc" / "kb"
        kb_dir.mkdir(parents=True)
        (kb_dir / "test.md").write_text("# test\n", encoding="utf-8")
        scanner = Scanner(root)
        result = scanner.scan(no_llm=True)
        assert any("Existing KB" in w for w in result.warnings)

    def test_scan_python_project(self, python_project: Path) -> None:
        scanner = Scanner(python_project)
        result = scanner.scan(no_llm=True)
        assert "python adapter" in result.recommendations
        meta = json.loads(result.kb_files["meta.json"])
        assert "Python" in meta["languages"]

    def test_scan_python_detects_flask(self, python_project: Path) -> None:
        scanner = Scanner(python_project)
        result = scanner.scan(no_llm=True)
        meta = json.loads(result.kb_files["meta.json"])
        assert "flask" in meta["frameworks"]

    def test_scan_java_project(self, java_project: Path) -> None:
        scanner = Scanner(java_project)
        result = scanner.scan(no_llm=True)
        assert "dongboot adapter" in result.recommendations
        meta = json.loads(result.kb_files["meta.json"])
        assert "Java" in meta["languages"]

    def test_scan_java_detects_spring_boot(self, java_project: Path) -> None:
        scanner = Scanner(java_project)
        result = scanner.scan(no_llm=True)
        meta = json.loads(result.kb_files["meta.json"])
        assert "spring-boot" in meta["frameworks"]

    def test_scan_java_detects_dongboot(self, java_project: Path) -> None:
        scanner = Scanner(java_project)
        result = scanner.scan(no_llm=True)
        assert "dongboot adapter" in result.recommendations
        meta = json.loads(result.kb_files["meta.json"])
        assert "dongboot" in meta["frameworks"]

    def test_scan_go_project(self, go_project: Path) -> None:
        scanner = Scanner(go_project)
        result = scanner.scan(no_llm=True)
        assert "go adapter" in result.recommendations
        meta = json.loads(result.kb_files["meta.json"])
        assert "Go" in meta["languages"]
        assert "gin" in meta["frameworks"]

    def test_scan_next_steps(self, project_root: Path) -> None:
        scanner = Scanner(project_root)
        result = scanner.scan(no_llm=True)
        assert len(result.next_steps) > 0
        assert any("Review" in s for s in result.next_steps)


class TestScannerManifestParsers:
    """Test individual manifest parsers."""

    def test_parse_package_json(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_package_json
        pkg = {"name": "test", "dependencies": {"react": "^18"}, "devDependencies": {"jest": "^29"}}
        p = tmp_path / "package.json"
        p.write_text(json.dinternal-monitorings(pkg), encoding="utf-8")
        result = _parse_package_json(p)
        assert result["name"] == "test"
        assert "react" in result["dependencies"]
        assert "jest" in result["devDependencies"]

    def test_parse_pyproject_toml(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_pyproject_toml
        content = '[project]\nname = "my-app"\ndependencies = [\n    "flask>=3.0",\n    "requests>=2.31",\n]\n'
        p = tmp_path / "pyproject.toml"
        p.write_text(content, encoding="utf-8")
        result = _parse_pyproject_toml(p)
        assert result["name"] == "my-app"
        assert "flask" in result["dependencies"]
        assert "requests" in result["dependencies"]

    def test_parse_pom_xml(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_pom_xml
        pom = """<?xml version="1.0"?>
<project>
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <dependencies>
    <dependency>
      <artifactId>spring-boot-starter</artifactId>
    </dependency>
  </dependencies>
</project>"""
        p = tmp_path / "pom.xml"
        p.write_text(pom, encoding="utf-8")
        result = _parse_pom_xml(p)
        assert result["groupId"] == "com.example"
        assert result["artifactId"] == "my-app"
        assert "spring-boot-starter" in result["dependencies"]

    def test_parse_go_mod(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_go_mod
        gomod = """module github.com/example/myapp

go 1.21

require (
\tgithub.com/gin-gonic/gin v1.9.0
)
"""
        p = tmp_path / "go.mod"
        p.write_text(gomod, encoding="utf-8")
        result = _parse_go_mod(p)
        assert result["module"] == "github.com/example/myapp"
        assert any("gin-gonic" in r for r in result["requires"])

    def test_parse_cargo_toml(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_cargo_toml
        cargo = """[package]
name = "my-crate"

[dependencies]
tokio = "1"
serde = { version = "1" }
"""
        p = tmp_path / "Cargo.toml"
        p.write_text(cargo, encoding="utf-8")
        result = _parse_cargo_toml(p)
        assert result["name"] == "my-crate"
        assert "tokio" in result["dependencies"]
        assert "serde" in result["dependencies"]

    def test_parse_requirements_txt(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_requirements_txt
        content = "flask>=3.0\nrequests>=2.31\n# comment\n-r other.txt\n"
        p = tmp_path / "requirements.txt"
        p.write_text(content, encoding="utf-8")
        result = _parse_requirements_txt(p)
        assert "flask" in result["dependencies"]
        assert "requests" in result["dependencies"]
        assert len(result["dependencies"]) == 2

    def test_parse_package_json_invalid(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_package_json
        p = tmp_path / "package.json"
        p.write_text("not valid json{{{", encoding="utf-8")
        result = _parse_package_json(p)
        assert result == {}

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        from sdlc.kb.scanner import _parse_pyproject_toml
        result = _parse_pyproject_toml(tmp_path / "nonexistent")
        assert result == {}


# ===========================================================================
# Reconciler tests
# ===========================================================================


class TestReconciler:
    def test_run_returns_list(self, kb: KnowledgeBase) -> None:
        r = Reconciler(kb)
        result = r.run()
        assert isinstance(result, list)

    def test_run_no_issues_on_healthy_kb(self, kb: KnowledgeBase) -> None:
        r = Reconciler(kb)
        issues = r.run()
        assert isinstance(issues, list)

    def test_detects_empty_files(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        (root / "empty.md").write_text("", encoding="utf-8")
        (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        kb = KnowledgeBase(root)
        r = Reconciler(kb)
        issues = r.run()
        assert any("Empty KB file: empty.md" in i for i in issues)

    def test_detects_missing_conventions(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        (root / "architecture.md").write_text("# Arch\n", encoding="utf-8")
        kb = KnowledgeBase(root, scope="project")
        r = Reconciler(kb)
        issues = r.run()
        assert any("Missing critical KB file: conventions.md" in i for i in issues)

    def test_no_missing_conventions_for_global_scope(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        (root / "architecture.md").write_text("# Arch\n", encoding="utf-8")
        kb = KnowledgeBase(root, scope="global")
        r = Reconciler(kb)
        issues = r.run()
        assert not any("Missing critical KB file" in i for i in issues)

    def test_detects_duplicates(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        content = "# Same Content\n"
        (root / "file1.md").write_text(content, encoding="utf-8")
        (root / "file2.md").write_text(content, encoding="utf-8")
        (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        kb = KnowledgeBase(root)
        r = Reconciler(kb)
        issues = r.run()
        assert any("Duplicate content" in i for i in issues)

    def test_detects_fingerprint_mismatch(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        (root / "stale.md").write_text("# Old Content\n", encoding="utf-8")
        kb = KnowledgeBase(root)
        (root / "stale.md").write_text("# New Content\n", encoding="utf-8")
        r = Reconciler(kb)
        issues = r.run()
        assert any("Fingerprint mismatch" in i for i in issues)

    def test_emits_audit_event(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        kb = KnowledgeBase(root)
        audit = AuditLogger(tmp_path / "audit.jsonl")
        r = Reconciler(kb, audit=audit)
        r.run()
        events = list(audit.query(event_type=AuditEventType.KB_UPDATED))
        assert len(events) >= 1
        assert events[0]["payload"]["action"] == "reconcile"

    def test_no_audit_no_crash(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        kb = KnowledgeBase(root)
        r = Reconciler(kb, audit=None)
        issues = r.run()
        assert isinstance(issues, list)

    def test_with_state_store(self, tmp_path: Path) -> None:
        from sdlc.state import StateStore
        root = tmp_path / "kb"
        root.mkdir()
        (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        kb = KnowledgeBase(root)
        state = StateStore(tmp_path / "state.db")
        r = Reconciler(kb, state=state)
        issues = r.run()
        assert isinstance(issues, list)

    def test_detects_missing_file_on_disk(self, tmp_path: Path) -> None:
        root = tmp_path / "kb"
        root.mkdir()
        (root / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        (root / "vanishing.md").write_text("# Will Vanish\n", encoding="utf-8")
        kb = KnowledgeBase(root)
        (root / "vanishing.md").unlink()
        r = Reconciler(kb)
        issues = r.run()
        assert any("Missing KB file on disk" in i for i in issues)


# ===========================================================================
# Model tests
# ===========================================================================


class TestModels:
    def test_kb_layer(self, tmp_path: Path) -> None:
        layer = KBLayer(
            name="test.md", type="markdown", path=tmp_path / "test.md",
            fingerprint="abc123", last_modified="2025-01-01T00:00:00Z", size_bytes=42,
        )
        assert layer.name == "test.md"
        assert layer.type == "markdown"
        assert layer.size_bytes == 42

    def test_kb_delta_result_written(self) -> None:
        delta = KBDeltaResult(target="test.md", operation="append", content="hello", fingerprint="abc")
        assert not delta.skipped
        assert delta.skip_reason is None

    def test_kb_delta_result_skipped(self) -> None:
        delta = KBDeltaResult(target="test.md", operation="append", content="hello", fingerprint="abc", skipped=True, skip_reason="dedup")
        assert delta.skipped
        assert delta.skip_reason == "dedup"

    def test_scan_result_defaults(self) -> None:
        sr = ScanResult(kb_files={}, recommendations=[], warnings=[])
        assert sr.confidence == 0.0
        assert sr.next_steps == []
