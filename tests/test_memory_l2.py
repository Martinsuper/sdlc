"""Tests for MemoryL2 post-stage KB auto-update."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdlc.kb.memory import MemoryL2


@pytest.fixture
def kb_root(tmp_path: Path) -> Path:
    """Create a temporary KB root directory."""
    root = tmp_path / "kb"
    root.mkdir()
    return root


class TestMemoryL2OnStageComplete:
    def test_no_kb_root_returns_zero(self) -> None:
        m = MemoryL2(kb_root=None)
        result = m.on_stage_complete("stage-1", {"status": "COMPLETED"})
        assert result == 0

    def test_nonexistent_kb_root_returns_zero(self, tmp_path: Path) -> None:
        m = MemoryL2(kb_root=tmp_path / "nonexistent")
        result = m.on_stage_complete("stage-1", {"status": "COMPLETED"})
        assert result == 0

    def test_empty_result_returns_zero(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        result = m.on_stage_complete("stage-1", {"status": "COMPLETED"})
        assert result == 0

    def test_writes_violation_learnings(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        stage_result = {
            "status": "FAILED",
            "rule_violations": [
                {"id": "R001", "level": "MUST", "message": "No tests found"},
            ],
        }
        count = m.on_stage_complete("design", stage_result, pipeline_id="p-1")
        assert count == 1

        memory_dir = kb_root / "memory"
        assert memory_dir.exists()
        files = list(memory_dir.glob("design-*.json"))
        assert len(files) == 1

        data = json.loads(files[0].read_text())
        assert data["stage_id"] == "design"
        assert data["pipeline_id"] == "p-1"
        assert len(data["learnings"]) == 1
        assert data["learnings"][0]["type"] == "rule_violation"
        assert data["learnings"][0]["rule_id"] == "R001"

    def test_writes_gate_decision_learning(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        stage_result = {
            "status": "COMPLETED",
            "gate_decision": {
                "gate_id": "G001",
                "action": "block",
                "reason": "Must violation detected",
            },
        }
        count = m.on_stage_complete("review", stage_result)
        assert count == 1

        files = list((kb_root / "memory").glob("review-*.json"))
        data = json.loads(files[0].read_text())
        assert data["learnings"][0]["type"] == "gate_decision"
        assert data["learnings"][0]["gate_id"] == "G001"

    def test_writes_error_learnings(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        stage_result = {
            "status": "FAILED",
            "error": "Timeout exceeded",
        }
        count = m.on_stage_complete("deploy", stage_result)
        assert count == 1

        files = list((kb_root / "memory").glob("deploy-*.json"))
        data = json.loads(files[0].read_text())
        assert data["learnings"][0]["type"] == "error"
        assert "Timeout exceeded" in data["learnings"][0]["message"]

    def test_writes_errors_from_list(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        stage_result = {
            "status": "FAILED",
            "errors": ["Error A", "Error B"],
        }
        count = m.on_stage_complete("test", stage_result)
        assert count == 2

        files = list((kb_root / "memory").glob("test-*.json"))
        data = json.loads(files[0].read_text())
        assert len(data["learnings"]) == 2

    def test_multiple_learnings_combined(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        stage_result = {
            "status": "FAILED",
            "rule_violations": [
                {"id": "R001", "level": "MUST", "message": "No tests"},
                {"id": "R002", "level": "SHOULD", "message": "Missing docs"},
            ],
            "gate_decision": {
                "gate_id": "G001",
                "action": "block",
                "reason": "Must violation",
            },
            "error": "Something went wrong",
        }
        count = m.on_stage_complete("review", stage_result, pipeline_id="p-2")
        assert count == 4  # 2 violations + 1 gate + 1 error

    def test_creates_memory_directory(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        assert not (kb_root / "memory").exists()
        m.on_stage_complete("stage-1", {"error": "fail"})
        assert (kb_root / "memory").exists()


class TestMemoryL2GetRecentLearnings:
    def test_empty_memory_returns_empty(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        assert m.get_recent_learnings() == []

    def test_no_kb_root_returns_empty(self) -> None:
        m = MemoryL2(kb_root=None)
        assert m.get_recent_learnings() == []

    def test_retrieves_recent_learnings(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        m.on_stage_complete("design", {"error": "err1"})
        m.on_stage_complete("review", {"error": "err2"})

        results = m.get_recent_learnings()
        assert len(results) == 2

    def test_filters_by_stage_id(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        m.on_stage_complete("design", {"error": "err1"})
        m.on_stage_complete("review", {"error": "err2"})

        results = m.get_recent_learnings(stage_id="design")
        assert len(results) == 1
        assert results[0]["stage_id"] == "design"

    def test_respects_limit(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        for i in range(5):
            m.on_stage_complete(f"stage-{i}", {"error": f"err{i}"})

        results = m.get_recent_learnings(limit=2)
        assert len(results) == 2

    def test_handles_corrupted_json(self, kb_root: Path) -> None:
        m = MemoryL2(kb_root=kb_root)
        memory_dir = kb_root / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "bad-stage-20250101T000000Z.json").write_text("not valid json{")
        m.on_stage_complete("good-stage", {"error": "ok"})

        results = m.get_recent_learnings()
        assert len(results) == 1
        assert results[0]["stage_id"] == "good-stage"
