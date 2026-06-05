import json
from pathlib import Path

from sdlc.audit.events import AuditEventType
from sdlc.audit.logger import AuditLogger
from sdlc.audit.query import count_events, get_latest, summarize


class TestAuditEventType:
    def test_has_at_least_25_members(self):
        assert len(AuditEventType) >= 25

    def test_is_str_enum(self):
        assert isinstance(AuditEventType.PIPELINE_START, str)
        assert AuditEventType.PIPELINE_START.value == "pipeline_start"

    def test_all_values_unique(self):
        values = [e.value for e in AuditEventType]
        assert len(values) == len(set(values))


class TestAuditLogger:
    def test_emit_creates_file_and_writes_jsonl(self, tmp_path: Path):
        log_path = tmp_path / "audit" / "test.jsonl"
        logger = AuditLogger(log_path)
        assert not log_path.is_file()
        logger.emit(AuditEventType.PIPELINE_START, {"detail": "ok"}, pipeline_id="p1")
        assert log_path.is_file()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["type"] == "pipeline_start"
        assert event["pipeline_id"] == "p1"
        assert event["payload"] == {"detail": "ok"}
        assert "ts" in event

    def test_emit_multiple_and_query_by_event_type(self, tmp_path: Path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path)
        logger.emit(AuditEventType.PIPELINE_START, {}, pipeline_id="p1")
        logger.emit(AuditEventType.STAGE_START, {"stage": "s1"}, pipeline_id="p1")
        logger.emit(AuditEventType.PIPELINE_END, {}, pipeline_id="p1")
        logger.emit(AuditEventType.STAGE_START, {"stage": "s2"}, pipeline_id="p1")
        results = list(logger.query(event_type=AuditEventType.STAGE_START))
        assert len(results) == 2
        assert results[0]["payload"]["stage"] == "s2"
        assert results[1]["payload"]["stage"] == "s1"

    def test_query_by_pipeline_id(self, tmp_path: Path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path)
        logger.emit(AuditEventType.PIPELINE_START, {}, pipeline_id="p1")
        logger.emit(AuditEventType.PIPELINE_START, {}, pipeline_id="p2")
        logger.emit(AuditEventType.PIPELINE_END, {}, pipeline_id="p1")
        results = list(logger.query(pipeline_id="p2"))
        assert len(results) == 1
        assert results[0]["pipeline_id"] == "p2"

    def test_query_empty_file_no_error(self, tmp_path: Path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path)
        results = list(logger.query())
        assert results == []

    def test_query_nonexistent_file_no_error(self, tmp_path: Path):
        log_path = tmp_path / "nope" / "audit.jsonl"
        logger = AuditLogger(log_path)
        results = list(logger.query())
        assert results == []

    def test_query_with_string_event_type(self, tmp_path: Path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path)
        logger.emit(AuditEventType.LLM_CALLED, {"model": "gpt-4"}, pipeline_id="p1")
        results = list(logger.query(event_type="llm_called"))
        assert len(results) == 1


class TestQueryHelpers:
    def _make_logger(self, tmp_path: Path) -> AuditLogger:
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path)
        logger.emit(AuditEventType.PIPELINE_START, {}, pipeline_id="p1")
        logger.emit(AuditEventType.STAGE_START, {"stage": "s1"}, pipeline_id="p1")
        logger.emit(AuditEventType.STAGE_END, {"stage": "s1"}, pipeline_id="p1")
        logger.emit(AuditEventType.PIPELINE_END, {}, pipeline_id="p1")
        logger.emit(AuditEventType.PIPELINE_START, {}, pipeline_id="p2")
        return logger

    def test_count_events(self, tmp_path: Path):
        logger = self._make_logger(tmp_path)
        assert count_events(logger) == 5
        assert count_events(logger, event_type=AuditEventType.PIPELINE_START) == 2
        assert count_events(logger, pipeline_id="p1") == 4

    def test_summarize(self, tmp_path: Path):
        logger = self._make_logger(tmp_path)
        summary = summarize(logger)
        assert summary["pipeline_start"] == 2
        assert summary["stage_start"] == 1
        assert summary["stage_end"] == 1
        assert summary["pipeline_end"] == 1

    def test_summarize_with_pipeline_id(self, tmp_path: Path):
        logger = self._make_logger(tmp_path)
        summary = summarize(logger, pipeline_id="p1")
        assert summary["pipeline_start"] == 1
        assert summary["stage_start"] == 1
        assert summary["stage_end"] == 1
        assert summary["pipeline_end"] == 1
        assert "pipeline_start" not in summary or summary.get("pipeline_start", 0) <= 1

    def test_get_latest(self, tmp_path: Path):
        logger = self._make_logger(tmp_path)
        latest = get_latest(logger, n=2)
        assert len(latest) == 2
        assert latest[0]["type"] == "pipeline_start"
        assert latest[0]["pipeline_id"] == "p2"

    def test_get_latest_with_event_type(self, tmp_path: Path):
        logger = self._make_logger(tmp_path)
        latest = get_latest(logger, event_type=AuditEventType.PIPELINE_START, n=1)
        assert len(latest) == 1
        assert latest[0]["pipeline_id"] == "p2"
