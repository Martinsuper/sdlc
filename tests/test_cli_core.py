"""Tests for core CLI commands."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from sdlc.audit.events import AuditEventType
from sdlc.audit.logger import AuditLogger
from sdlc.state.store import StateStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HOME_PATCH = "sdlc.utils.paths.sdlc_home"


def _make_store(tmp_path: Path) -> StateStore:
    db_path = tmp_path / "state.db"
    return StateStore(db_path)


def _seed_pipeline(store: StateStore, pid: str = "pipe-1", **overrides: str) -> None:
    store.save_pipeline(
        pipeline_id=pid,
        entry_kind=overrides.get("entry_kind", "feature"),
        profile_id=overrides.get("profile_id", "default"),
        status=overrides.get("status", "completed"),
    )


def _make_audit(tmp_path: Path) -> AuditLogger:
    audit_path = tmp_path / "audit.jsonl"
    return AuditLogger(audit_path)


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_no_input_shows_error(self) -> None:
        from sdlc.cli.run_cmd import run

        runner = CliRunner()
        result = runner.invoke(run, [])
        assert result.exit_code != 0
        assert "Please provide input" in result.output

    def test_text_input_detects_entry(self) -> None:
        from sdlc.cli.run_cmd import run

        runner = CliRunner()
        with patch("sdlc.cli.deps.build_deps") as mock_deps:
            from sdlc.core.models import PipelineResult
            mock_deps.return_value.coordinator.run = AsyncMock(
                return_value=PipelineResult(
                    pipeline_id="test-1", status="completed", stage_results=[], total_cost_usd=0.0
                )
            )
            result = runner.invoke(run, ["fix bug in login"])
        assert result.exit_code == 0
        assert "Entry detected" in result.output

    def test_file_input(self, tmp_path: Path) -> None:
        from sdlc.cli.run_cmd import run

        f = tmp_path / "input.txt"
        f.write_text("implement a new feature for dashboard")
        runner = CliRunner()
        with patch("sdlc.cli.deps.build_deps") as mock_deps:
            from sdlc.core.models import PipelineResult
            mock_deps.return_value.coordinator.run = AsyncMock(
                return_value=PipelineResult(
                    pipeline_id="test-1", status="completed", stage_results=[], total_cost_usd=0.0
                )
            )
            result = runner.invoke(run, [f"@{f}"])
        assert result.exit_code == 0
        assert "feature" in result.output

    def test_file_not_found(self) -> None:
        from sdlc.cli.run_cmd import run

        runner = CliRunner()
        result = runner.invoke(run, ["@/nonexistent/file.txt"])
        assert result.exit_code != 0
        assert "File not found" in result.output

    def test_entry_kind_override(self) -> None:
        from sdlc.cli.run_cmd import run

        runner = CliRunner()
        with patch("sdlc.cli.deps.build_deps") as mock_deps:
            from sdlc.core.models import PipelineResult
            mock_deps.return_value.coordinator.run = AsyncMock(
                return_value=PipelineResult(
                    pipeline_id="test-1", status="completed", stage_results=[], total_cost_usd=0.0
                )
            )
            result = runner.invoke(run, ["some text", "-e", "hotfix"])
        assert result.exit_code == 0
        assert "hotfix" in result.output

    def test_dry_run(self) -> None:
        from sdlc.cli.run_cmd import run

        runner = CliRunner()
        result = runner.invoke(run, ["some text", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run mode" in result.output

    def test_severity_option(self) -> None:
        from sdlc.cli.run_cmd import run

        runner = CliRunner()
        with patch("sdlc.cli.deps.build_deps") as mock_deps:
            from sdlc.core.models import PipelineResult
            mock_deps.return_value.coordinator.run = AsyncMock(
                return_value=PipelineResult(
                    pipeline_id="test-1", status="completed", stage_results=[], total_cost_usd=0.0
                )
            )
            result = runner.invoke(run, ["some text", "--severity", "P0"])
        assert result.exit_code == 0
        assert "P0" in result.output


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


class TestInitCommand:
    def test_creates_sdlc_dir(self, tmp_path: Path) -> None:
        from sdlc.cli.init_cmd import init

        runner = CliRunner()
        result = runner.invoke(init, [str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / ".sdlc").is_dir()
        assert (tmp_path / ".sdlc" / "config.toml").exists()

    def test_creates_kb_structure(self, tmp_path: Path) -> None:
        from sdlc.cli.init_cmd import init

        runner = CliRunner()
        result = runner.invoke(init, [str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "doc" / "kb" / "rules" / "MUST.yaml").exists()
        assert (tmp_path / "doc" / "kb" / "conventions.md").exists()

    def test_existing_dir_without_force(self, tmp_path: Path) -> None:
        from sdlc.cli.init_cmd import init

        (tmp_path / ".sdlc").mkdir()
        runner = CliRunner()
        result = runner.invoke(init, [str(tmp_path)])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_force_overwrites(self, tmp_path: Path) -> None:
        from sdlc.cli.init_cmd import init

        (tmp_path / ".sdlc").mkdir()
        runner = CliRunner()
        result = runner.invoke(init, [str(tmp_path), "--force"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower() or "Created" in result.output

    def test_template_empty(self, tmp_path: Path) -> None:
        from sdlc.cli.init_cmd import init

        runner = CliRunner()
        result = runner.invoke(init, [str(tmp_path), "--template", "empty"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------


class TestStatusCommand:
    def test_no_db_shows_message(self, tmp_path: Path) -> None:
        from sdlc.cli.status_cmd import status

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(status, [])
            assert "No pipelines found" in result.output

    def test_list_pipelines(self, tmp_path: Path) -> None:
        from sdlc.cli.status_cmd import status

        store = _make_store(tmp_path)
        _seed_pipeline(store, "p1", status="completed")
        _seed_pipeline(store, "p2", status="failed")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(status, [])
            assert result.exit_code == 0
            assert "p1" in result.output or "Pipelines" in result.output

    def test_specific_pipeline(self, tmp_path: Path) -> None:
        from sdlc.cli.status_cmd import status

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(status, ["pipe-1"])
            assert result.exit_code == 0
            assert "pipe-1" in result.output

    def test_pipeline_not_found(self, tmp_path: Path) -> None:
        from sdlc.cli.status_cmd import status

        _make_store(tmp_path)  # create DB so it exists

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(status, ["nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_json_output(self, tmp_path: Path) -> None:
        from sdlc.cli.status_cmd import status

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(status, ["pipe-1", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["id"] == "pipe-1"

    def test_json_list_output(self, tmp_path: Path) -> None:
        from sdlc.cli.status_cmd import status

        store = _make_store(tmp_path)
        _seed_pipeline(store, "p1")
        _seed_pipeline(store, "p2")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(status, ["--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) == 2

    def test_empty_pipelines_list(self, tmp_path: Path) -> None:
        from sdlc.cli.status_cmd import status

        _make_store(tmp_path)  # create DB with no pipelines

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(status, [])
            assert "No pipelines found" in result.output


# ---------------------------------------------------------------------------
# resume command
# ---------------------------------------------------------------------------


class TestResumeCommand:
    def test_no_db_shows_error(self, tmp_path: Path) -> None:
        from sdlc.cli.resume_cmd import resume

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(resume, ["pipe-1"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_resume_existing_pipeline(self, tmp_path: Path) -> None:
        from sdlc.cli.resume_cmd import resume

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1", status="failed")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(resume, ["pipe-1"])
            assert result.exit_code == 0
            assert "Resuming pipeline" in result.output

    def test_resume_nonexistent_pipeline(self, tmp_path: Path) -> None:
        from sdlc.cli.resume_cmd import resume

        _make_store(tmp_path)

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(resume, ["nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_resume_with_from_stage(self, tmp_path: Path) -> None:
        from sdlc.cli.resume_cmd import resume

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1", status="paused")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(resume, ["pipe-1", "--from-stage", "implement"])
            assert result.exit_code == 0
            assert "implement" in result.output

    def test_resume_with_reset_gates(self, tmp_path: Path) -> None:
        from sdlc.cli.resume_cmd import resume

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1", status="paused")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(resume, ["pipe-1", "--reset-gates"])
            assert result.exit_code == 0
            assert "Gates will be reset" in result.output


# ---------------------------------------------------------------------------
# trace command
# ---------------------------------------------------------------------------


class TestTraceCommand:
    def test_no_audit_log_shows_error(self, tmp_path: Path) -> None:
        from sdlc.cli.trace_cmd import trace

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(trace, ["pipe-1"])
            assert result.exit_code != 0
            assert "No audit log" in result.output

    def test_trace_with_events(self, tmp_path: Path) -> None:
        from sdlc.cli.trace_cmd import trace

        audit = _make_audit(tmp_path)
        audit.emit(AuditEventType.PIPELINE_START, {"msg": "started"}, pipeline_id="pipe-1")
        audit.emit(AuditEventType.STAGE_START, {"stage": "design"}, pipeline_id="pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(trace, ["pipe-1"])
            assert result.exit_code == 0
            assert "pipeline_start" in result.output
            assert "stage_start" in result.output

    def test_trace_no_events_for_pipeline(self, tmp_path: Path) -> None:
        from sdlc.cli.trace_cmd import trace

        audit = _make_audit(tmp_path)
        audit.emit(AuditEventType.PIPELINE_START, {"msg": "started"}, pipeline_id="other-pipe")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(trace, ["pipe-1"])
            assert result.exit_code == 0
            assert "No events found" in result.output

    def test_trace_json_output(self, tmp_path: Path) -> None:
        from sdlc.cli.trace_cmd import trace

        audit = _make_audit(tmp_path)
        audit.emit(AuditEventType.PIPELINE_START, {"msg": "started"}, pipeline_id="pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(trace, ["pipe-1", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)

    def test_trace_filter_by_event_type(self, tmp_path: Path) -> None:
        from sdlc.cli.trace_cmd import trace

        audit = _make_audit(tmp_path)
        audit.emit(AuditEventType.PIPELINE_START, {"msg": "started"}, pipeline_id="pipe-1")
        audit.emit(AuditEventType.STAGE_START, {"stage": "design"}, pipeline_id="pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(trace, ["pipe-1", "--type", "stage_start"])
            assert result.exit_code == 0
            assert "stage_start" in result.output


# ---------------------------------------------------------------------------
# replay command
# ---------------------------------------------------------------------------


class TestReplayCommand:
    def test_no_db_shows_error(self, tmp_path: Path) -> None:
        from sdlc.cli.replay_cmd import replay

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(replay, ["pipe-1"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_replay_existing_pipeline(self, tmp_path: Path) -> None:
        from sdlc.cli.replay_cmd import replay

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(replay, ["pipe-1"])
            assert result.exit_code == 0
            assert "Replaying pipeline" in result.output

    def test_replay_nonexistent_pipeline(self, tmp_path: Path) -> None:
        from sdlc.cli.replay_cmd import replay

        _make_store(tmp_path)

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(replay, ["nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_replay_with_stage_and_fresh(self, tmp_path: Path) -> None:
        from sdlc.cli.replay_cmd import replay

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(replay, ["pipe-1", "--stage", "implement", "--fresh"])
            assert result.exit_code == 0
            assert "From stage: implement" in result.output
            assert "Fresh mode" in result.output


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------


class TestExportCommand:
    def test_no_db_shows_error(self, tmp_path: Path) -> None:
        from sdlc.cli.export_cmd import export

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(export, ["pipe-1"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_export_json_to_stdout(self, tmp_path: Path) -> None:
        from sdlc.cli.export_cmd import export

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(export, ["pipe-1"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["id"] == "pipe-1"

    def test_export_json_to_file(self, tmp_path: Path) -> None:
        from sdlc.cli.export_cmd import export

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")
        output_file = tmp_path / "export.json"

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(export, ["pipe-1", "-o", str(output_file)])
            assert result.exit_code == 0
            assert output_file.exists()
            data = json.loads(output_file.read_text())
            assert data["id"] == "pipe-1"

    def test_export_markdown(self, tmp_path: Path) -> None:
        from sdlc.cli.export_cmd import export

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(export, ["pipe-1", "--format", "markdown"])
            assert result.exit_code == 0
            assert "# Pipeline pipe-1" in result.output

    def test_export_yaml(self, tmp_path: Path) -> None:
        from sdlc.cli.export_cmd import export

        store = _make_store(tmp_path)
        _seed_pipeline(store, "pipe-1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(export, ["pipe-1", "--format", "yaml"])
            assert result.exit_code == 0
            assert "pipe-1" in result.output

    def test_export_pipeline_not_found(self, tmp_path: Path) -> None:
        from sdlc.cli.export_cmd import export

        _make_store(tmp_path)

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(export, ["nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# import command
# ---------------------------------------------------------------------------


class TestImportCommand:
    def test_import_json(self, tmp_path: Path) -> None:
        from sdlc.cli.import_cmd import import_cmd

        f = tmp_path / "data.json"
        f.write_text(json.dinternal-monitorings({"type": "pipeline", "id": "test", "status": "completed"}))
        runner = CliRunner()
        result = runner.invoke(import_cmd, [str(f)])
        assert result.exit_code == 0
        assert "Imported" in result.output
        assert "pipeline" in result.output

    def test_import_invalid_json(self, tmp_path: Path) -> None:
        from sdlc.cli.import_cmd import import_cmd

        f = tmp_path / "bad.json"
        f.write_text("not valid json {{{")
        runner = CliRunner()
        result = runner.invoke(import_cmd, [str(f)])
        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_import_yaml(self, tmp_path: Path) -> None:
        from sdlc.cli.import_cmd import import_cmd

        f = tmp_path / "data.yaml"
        f.write_text("type: pipeline\nid: test\n")
        runner = CliRunner()
        result = runner.invoke(import_cmd, [str(f), "--format", "yaml"])
        assert result.exit_code == 0
        assert "Imported" in result.output


# ---------------------------------------------------------------------------
# stats command
# ---------------------------------------------------------------------------


class TestStatsCommand:
    def test_no_db_shows_message(self, tmp_path: Path) -> None:
        from sdlc.cli.stats_cmd import stats

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(stats, [])
            assert "No data available" in result.output

    def test_stats_with_pipelines(self, tmp_path: Path) -> None:
        from sdlc.cli.stats_cmd import stats

        store = _make_store(tmp_path)
        _seed_pipeline(store, "p1", status="completed")
        _seed_pipeline(store, "p2", status="completed")
        _seed_pipeline(store, "p3", status="failed")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(stats, [])
            assert result.exit_code == 0
            assert "Total:        3" in result.output
            assert "Completed:    2" in result.output
            assert "Failed:       1" in result.output

    def test_stats_json_output(self, tmp_path: Path) -> None:
        from sdlc.cli.stats_cmd import stats

        store = _make_store(tmp_path)
        _seed_pipeline(store, "p1", status="completed")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(stats, ["--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total"] == 1
            assert data["completed"] == 1

    def test_stats_no_pipelines(self, tmp_path: Path) -> None:
        from sdlc.cli.stats_cmd import stats

        _make_store(tmp_path)  # DB exists but no pipelines

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(stats, [])
            assert "No pipelines found" in result.output

    def test_stats_by_model_and_by_stage(self, tmp_path: Path) -> None:
        from sdlc.cli.stats_cmd import stats

        store = _make_store(tmp_path)
        _seed_pipeline(store, "p1")

        with patch(_HOME_PATCH, return_value=tmp_path):
            runner = CliRunner()
            result = runner.invoke(stats, ["--by-model", "--by-stage"])
            assert result.exit_code == 0
            assert "by model" in result.output.lower()
            assert "by stage" in result.output.lower()
