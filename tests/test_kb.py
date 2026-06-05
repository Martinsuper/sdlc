"""Tests for sdlc.kb package."""

import hashlib
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
        assert len(layer.fingerprint) == 64  # sha256 hex digest length

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
            [
                {
                    "target": "architecture/new-section.md",
                    "operation": "append",
                    "content": "## New Section\nHello world",
                }
            ],
        )
        assert len(deltas) == 1
        d = deltas[0]
        assert not d.skipped
        assert d.operation == "append"
        assert d.target == "architecture/new-section.md"
        # File now exists on disk.
        assert (kb.root / "architecture/new-section.md").is_file()
        content = (kb.root / "architecture/new-section.md").read_text("utf-8")
        assert "Hello world" in content

    def test_update_after_stage_append_existing(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        # First append.
        writer.update_after_stage(
            "s1",
            [
                {
                    "target": "architecture/component-catalog.md",
                    "operation": "append",
                    "content": "## Appended",
                }
            ],
        )
        original = (kb.root / "architecture/component-catalog.md").read_text("utf-8")
        assert "## Appended" in original

    def test_fingerprint_dedup(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        upd = {
            "target": "architecture/component-catalog.md",
            "operation": "append",
            "content": "Dedup content",
        }
        d1 = writer.update_after_stage("s1", [upd])[0]
        assert not d1.skipped

        # Same content again should be skipped.
        d2 = writer.update_after_stage("s2", [upd])[0]
        assert d2.skipped
        assert d2.skip_reason == "duplicate fingerprint"

    def test_human_only_file_skipped(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        deltas = writer.update_after_stage(
            "s1",
            [
                {
                    "target": "conventions.md",
                    "operation": "append",
                    "content": "Should be skipped",
                }
            ],
        )
        d = deltas[0]
        assert d.skipped
        assert "human-only" in d.skip_reason

    def test_append_mode_creates_section_header(
        self, kb: KnowledgeBase
    ) -> None:
        writer = KBWriter(kb)
        writer.update_after_stage(
            "s1",
            [
                {
                    "target": "architecture/new-section.md",
                    "operation": "append",
                    "content": "Section body",
                }
            ],
        )
        content = (kb.root / "architecture/new-section.md").read_text("utf-8")
        assert "Auto-generated by SDLC stage" in content

    def test_update_mode_yaml(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        deltas = writer.update_after_stage(
            "s1",
            [
                {
                    "target": "architecture/deps.yaml",
                    "operation": "update",
                    "content": '{"new_key": "new_value"}',
                }
            ],
        )
        d = deltas[0]
        assert not d.skipped
        # Verify the YAML file was updated.
        from sdlc.utils.yaml_io import load_yaml

        data = load_yaml(kb.root / "architecture/deps.yaml")
        assert data["new_key"] == "new_value"

    def test_update_mode_missing_file_raises(
        self, kb: KnowledgeBase
    ) -> None:
        writer = KBWriter(kb)
        with pytest.raises(KBWriteConflictError, match="Cannot update"):
            writer.update_after_stage(
                "s1",
                [
                    {
                        "target": "nonexistent.yaml",
                        "operation": "update",
                        "content": "{}",
                    }
                ],
            )

    def test_unknown_operation_raises(
        self, kb: KnowledgeBase
    ) -> None:
        writer = KBWriter(kb)
        with pytest.raises(KBWriteConflictError, match="Unknown KB write operation"):
            writer.update_after_stage(
                "s1",
                [
                    {
                        "target": "architecture/new.md",
                        "operation": "delete",
                        "content": "oops",
                    }
                ],
            )

    def test_audit_events_emitted(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        writer.update_after_stage(
            "s1",
            [
                {
                    "target": "architecture/new-section.md",
                    "operation": "append",
                    "content": "Audit test",
                }
            ],
        )
        events = list(audit_log.query(event_type=AuditEventType.KB_UPDATED))
        assert len(events) >= 1
        assert events[0]["payload"]["action"] == "written"

    def test_audit_skip_event(
        self, kb: KnowledgeBase, audit_log: AuditLogger
    ) -> None:
        writer = KBWriter(kb, audit=audit_log)
        writer.update_after_stage(
            "s1",
            [
                {
                    "target": "conventions.md",
                    "operation": "append",
                    "content": "Skip audit",
                }
            ],
        )
        events = list(audit_log.query(event_type=AuditEventType.KB_UPDATED))
        assert len(events) == 1
        assert events[0]["payload"]["action"] == "skip_human_only"

    def test_no_audit_logger_does_not_crash(self, kb: KnowledgeBase) -> None:
        writer = KBWriter(kb, audit=None)
        deltas = writer.update_after_stage(
            "s1",
            [
                {
                    "target": "architecture/new.md",
                    "operation": "append",
                    "content": "No audit",
                }
            ],
        )
        assert len(deltas) == 1
        assert not deltas[0].skipped

    def test_idempotent_append(self, kb: KnowledgeBase) -> None:
        """Writing the same content twice (in the same writer) = same result."""
        writer = KBWriter(kb)
        upd = {
            "target": "architecture/idem.md",
            "operation": "append",
            "content": "Idempotent check",
        }
        d1 = writer.update_after_stage("s1", [upd])[0]
        assert not d1.skipped
        d2 = writer.update_after_stage("s2", [upd])[0]
        assert d2.skipped  # dedup kicks in

    def test_writer_refreshes_layer(
        self, kb: KnowledgeBase
    ) -> None:
        writer = KBWriter(kb)
        writer.update_after_stage(
            "s1",
            [
                {
                    "target": "architecture/new-layer.md",
                    "operation": "append",
                    "content": "Fresh layer",
                }
            ],
        )
        # The new file should now appear in kb.layers.
        assert kb.exists("architecture/new-layer.md")
        layer = kb.get("architecture/new-layer.md")
        assert layer.size_bytes > 0


# ===========================================================================
# Fingerprint tests
# ===========================================================================


class TestFingerprint:
    def test_compute_kb_fingerprint(self) -> None:
        content = "hello world"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert compute_kb_fingerprint(content) == expected

    def test_compute_kb_fingerprint_empty(self) -> None:
        assert compute_kb_fingerprint("") == hashlib.sha256(b"").hexdigest()

    def test_compute_layer_fingerprint(self, tmp_path: Path) -> None:
        p = tmp_path / "test.txt"
        p.write_text("file content", encoding="utf-8")
        expected = hashlib.sha256(b"file content").hexdigest()
        assert compute_layer_fingerprint(p) == expected

    def test_compute_layer_fingerprint_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            compute_layer_fingerprint(tmp_path / "gone.txt")


# ===========================================================================
# Scanner stub tests
# ===========================================================================


class TestScanner:
    def test_scan_raises_not_implemented(self, tmp_path: Path) -> None:
        scanner = Scanner(tmp_path)
        with pytest.raises(NotImplementedError, match="M2"):
            scanner.scan()

    def test_root_stored(self, tmp_path: Path) -> None:
        scanner = Scanner(tmp_path)
        assert scanner.root == tmp_path


# ===========================================================================
# Reconciler stub tests
# ===========================================================================


class TestReconciler:
    def test_run_raises_not_implemented(self) -> None:
        r = Reconciler()
        with pytest.raises(NotImplementedError, match="M2"):
            r.run()


# ===========================================================================
# Model tests
# ===========================================================================


class TestModels:
    def test_kb_layer(self, tmp_path: Path) -> None:
        layer = KBLayer(
            name="test.md",
            type="markdown",
            path=tmp_path / "test.md",
            fingerprint="abc123",
            last_modified="2025-01-01T00:00:00Z",
            size_bytes=42,
        )
        assert layer.name == "test.md"
        assert layer.type == "markdown"
        assert layer.size_bytes == 42

    def test_kb_delta_result_written(self) -> None:
        delta = KBDeltaResult(
            target="test.md",
            operation="append",
            content="hello",
            fingerprint="abc",
        )
        assert not delta.skipped
        assert delta.skip_reason is None

    def test_kb_delta_result_skipped(self) -> None:
        delta = KBDeltaResult(
            target="test.md",
            operation="append",
            content="hello",
            fingerprint="abc",
            skipped=True,
            skip_reason="dedup",
        )
        assert delta.skipped
        assert delta.skip_reason == "dedup"

    def test_scan_result_defaults(self) -> None:
        sr = ScanResult(
            kb_files={},
            recommendations=[],
            warnings=[],
        )
        assert sr.confidence == 0.0
        assert sr.next_steps == []
