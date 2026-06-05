import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from sdlc.state.models import Artifact, StageResult
from sdlc.state.schema import VALID_TRANSITIONS
from sdlc.state.snapshot import list_snapshots, take_snapshot
from sdlc.state.store import StateStore


@pytest.fixture
def store(tmp_dir):
    db_path = tmp_dir / "state.db"
    return StateStore(db_path)


@pytest.fixture
def store_with_pipeline(store):
    store.save_pipeline("p1", "commit", "profile-a", status="NEW")
    return store


class TestSchemaAndInit:
    def test_init_creates_db_file(self, tmp_dir):
        db_path = tmp_dir / "sub" / "state.db"
        StateStore(db_path)
        assert db_path.is_file()

    def test_init_creates_tables(self, store):
        row = store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pipelines'"
        ).fetchone()
        assert row is not None

    def test_valid_transitions(self):
        assert "RUNNING" in VALID_TRANSITIONS["PENDING"]
        assert "SUCCESS" in VALID_TRANSITIONS["RUNNING"]
        assert "FAILED" in VALID_TRANSITIONS["RUNNING"]
        assert "PENDING" in VALID_TRANSITIONS["FAILED"]
        assert len(VALID_TRANSITIONS["SUCCESS"]) == 0
        assert len(VALID_TRANSITIONS["CANCELLED"]) == 0


class TestPipeline:
    def test_save_and_load(self, store_with_pipeline):
        p = store_with_pipeline.load_pipeline("p1")
        assert p is not None
        assert p.id == "p1"
        assert p.entry_kind == "commit"
        assert p.profile_id == "profile-a"
        assert p.status == "NEW"

    def test_load_missing_returns_none(self, store):
        assert store.load_pipeline("missing") is None

    def test_update_status(self, store_with_pipeline):
        store_with_pipeline.update_pipeline_status("p1", "RUNNING")
        p = store_with_pipeline.load_pipeline("p1")
        assert p.status == "RUNNING"

    def test_list_pipelines(self, store):
        store.save_pipeline("p1", "commit", "prof1", status="NEW")
        store.save_pipeline("p2", "commit", "prof2", status="RUNNING")
        result = store.list_pipelines()
        assert len(result) == 2

    def test_list_pipelines_filter_status(self, store):
        store.save_pipeline("p1", "commit", "prof1", status="NEW")
        store.save_pipeline("p2", "commit", "prof2", status="RUNNING")
        result = store.list_pipelines(status="RUNNING")
        assert len(result) == 1
        assert result[0].id == "p2"

    def test_list_pipelines_with_since(self, store):
        store.save_pipeline("p1", "commit", "prof1", status="NEW")
        future = datetime.now(UTC) + timedelta(days=1)
        result = store.list_pipelines(since=future)
        assert len(result) == 0

    def test_delete_pipeline(self, store_with_pipeline):
        store_with_pipeline.delete_pipeline("p1")
        assert store_with_pipeline.load_pipeline("p1") is None

    def test_delete_pipeline_cascades_stages(self, store_with_pipeline):
        store_with_pipeline.save_stage_result(
            StageResult(
                id="s1",
                pipeline_id="p1",
                stage_def_id="sd1",
                status="SUCCESS",
                started_at=datetime.now(UTC).isoformat(),
            )
        )
        store_with_pipeline.delete_pipeline("p1")
        assert store_with_pipeline.load_stage_result("p1", "s1") is None


class TestStage:
    def test_save_and_load(self, store_with_pipeline):
        result = StageResult(
            id="s1",
            pipeline_id="p1",
            stage_def_id="sd1",
            status="SUCCESS",
            started_at=datetime.now(UTC).isoformat(),
        )
        store_with_pipeline.save_stage_result(result)
        loaded = store_with_pipeline.load_stage_result("p1", "s1")
        assert loaded is not None
        assert loaded.stage_def_id == "sd1"
        assert loaded.status == "SUCCESS"

    def test_load_missing_returns_none(self, store_with_pipeline):
        assert store_with_pipeline.load_stage_result("p1", "missing") is None

    def test_list_stage_results(self, store_with_pipeline):
        store_with_pipeline.save_stage_result(
            StageResult(id="s1", pipeline_id="p1", stage_def_id="sd1", status="SUCCESS")
        )
        store_with_pipeline.save_stage_result(
            StageResult(id="s2", pipeline_id="p1", stage_def_id="sd2", status="RUNNING")
        )
        results = store_with_pipeline.list_stage_results("p1")
        assert len(results) == 2


class TestArtifact:
    def test_register_and_list(self, store_with_pipeline):
        now = datetime.now(UTC).isoformat()
        art = Artifact(
            id="a1",
            pipeline_id="p1",
            stage_id="s1",
            type="doc",
            path="/tmp/doc.md",
            created_at=now,
        )
        store_with_pipeline.register_artifact(art)
        arts = store_with_pipeline.list_artifacts("p1")
        assert len(arts) == 1
        assert arts[0].type == "doc"

    def test_list_artifacts_filter_type(self, store_with_pipeline):
        now = datetime.now(UTC).isoformat()
        store_with_pipeline.register_artifact(
            Artifact(id="a1", pipeline_id="p1", stage_id="s1", type="doc", created_at=now)
        )
        store_with_pipeline.register_artifact(
            Artifact(id="a2", pipeline_id="p1", stage_id="s1", type="code", created_at=now)
        )
        arts = store_with_pipeline.list_artifacts("p1", type="doc")
        assert len(arts) == 1

    def test_get_artifact(self, store_with_pipeline):
        now = datetime.now(UTC).isoformat()
        store_with_pipeline.register_artifact(
            Artifact(id="a1", pipeline_id="p1", stage_id="s1", type="doc", created_at=now)
        )
        art = store_with_pipeline.get_artifact("a1")
        assert art is not None
        assert art.id == "a1"

    def test_get_artifact_missing(self, store):
        assert store.get_artifact("missing") is None


class TestLLMCall:
    def test_record_and_cost(self, store_with_pipeline):
        store_with_pipeline.record_llm_call(
            pipeline_id="p1",
            stage_id="s1",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
            duration_ms=1200,
            cached=False,
        )
        cost = store_with_pipeline.get_pipeline_cost("p1")
        assert cost == pytest.approx(0.05)

    def test_pipeline_cost_zero(self, store_with_pipeline):
        cost = store_with_pipeline.get_pipeline_cost("p1")
        assert cost == 0.0

    def test_cost_daily(self, store_with_pipeline):
        store_with_pipeline.record_llm_call(
            pipeline_id="p1",
            stage_id=None,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
            duration_ms=1000,
            cached=False,
        )
        since = datetime.now(UTC) - timedelta(days=1)
        stats = store_with_pipeline.get_cost_daily(since)
        assert len(stats) >= 1
        assert stats[0].model == "gpt-4"
        assert stats[0].calls == 1


class TestKBDelta:
    def test_record_and_get(self, store_with_pipeline):
        kid = store_with_pipeline.record_kb_delta(
            pipeline_id="p1",
            stage_id="s1",
            target="docs/api.md",
            operation="update",
            fingerprint="abc123",
        )
        assert isinstance(kid, int)
        since = datetime.now(UTC) - timedelta(hours=1)
        deltas = store_with_pipeline.get_kb_deltas("docs/api.md", since)
        assert len(deltas) == 1
        assert deltas[0].fingerprint == "abc123"

    def test_get_kb_deltas_no_match(self, store_with_pipeline):
        since = datetime.now(UTC) - timedelta(hours=1)
        deltas = store_with_pipeline.get_kb_deltas("nonexistent", since)
        assert len(deltas) == 0


class TestResumeToken:
    def test_save_and_verify_valid(self, store_with_pipeline):
        expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        store_with_pipeline.save_resume_token("p1", "tok123", expires)
        assert store_with_pipeline.verify_resume_token("p1", "tok123") is True

    def test_verify_expired_token(self, store_with_pipeline):
        expires = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        store_with_pipeline.save_resume_token("p1", "tok123", expires)
        assert store_with_pipeline.verify_resume_token("p1", "tok123") is False

    def test_verify_wrong_token(self, store_with_pipeline):
        expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        store_with_pipeline.save_resume_token("p1", "tok123", expires)
        assert store_with_pipeline.verify_resume_token("p1", "wrong") is False

    def test_verify_missing_pipeline(self, store_with_pipeline):
        assert store_with_pipeline.verify_resume_token("missing", "tok") is False

    def test_get_resume_state(self, store_with_pipeline):
        expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        store_with_pipeline.save_resume_token("p1", "tok123", expires)
        state = store_with_pipeline.get_resume_state("p1")
        assert state is not None
        assert state.token == "tok123"

    def test_get_resume_state_missing(self, store):
        assert store.get_resume_state("missing") is None


class TestTransaction:
    def test_rollback_on_error(self, store_with_pipeline):
        try:
            with store_with_pipeline.transaction() as tx:
                tx.execute(
                    "INSERT INTO pipelines (id, entry_kind, profile_id, status, "
                    "created_at, updated_at, meta_json) VALUES (?,?,?,?,?,?,?)",
                    ("p2", "commit", "prof", "NEW", "t", "t", "{}"),
                )
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass
        assert store_with_pipeline.load_pipeline("p2") is None


class TestBackup:
    def test_backup_creates_file(self, store_with_pipeline, tmp_dir):
        dest = tmp_dir / "backup.db"
        store_with_pipeline.backup(dest)
        assert dest.is_file()
        backup = sqlite3.connect(str(dest))
        row = backup.execute("SELECT COUNT(*) FROM pipelines").fetchone()
        backup.close()
        assert row[0] == 1


class TestSnapshot:
    def test_take_snapshot_writes_file(self, store_with_pipeline, tmp_dir):
        snap_dir = tmp_dir / "snaps"
        snapshot = take_snapshot(store_with_pipeline, "p1", snap_dir)
        assert "pipeline_id" in snapshot
        assert snapshot["pipeline_id"] == "p1"
        pipe_dir = snap_dir / "p1"
        assert pipe_dir.is_dir()
        files = list(pipe_dir.glob("*.snap.json"))
        assert len(files) >= 1

    def test_take_snapshot_with_stages(self, store_with_pipeline, tmp_dir):
        snap_dir = tmp_dir / "snaps"
        store_with_pipeline.save_stage_result(
            StageResult(id="s1", pipeline_id="p1", stage_def_id="sd1", status="SUCCESS")
        )
        snapshot = take_snapshot(store_with_pipeline, "p1", snap_dir)
        assert snapshot["stage_id"] == "sd1"
        assert len(snapshot["stages"]) == 1

    def test_list_snapshots(self, store_with_pipeline, tmp_dir):
        snap_dir = tmp_dir / "snaps"
        take_snapshot(store_with_pipeline, "p1", snap_dir)
        snaps = list_snapshots(snap_dir, "p1")
        assert len(snaps) == 1

    def test_list_snapshots_empty(self, tmp_dir):
        snap_dir = tmp_dir / "snaps"
        snaps = list_snapshots(snap_dir, "nonexistent")
        assert snaps == []

    def test_snapshot_prune_keeps_latest_five(self, store_with_pipeline, tmp_dir):
        snap_dir = tmp_dir / "snaps"
        for i in range(7):
            store_with_pipeline.save_stage_result(
                StageResult(
                    id=f"s{i}",
                    pipeline_id="p1",
                    stage_def_id=f"sd{i}",
                    status="SUCCESS",
                )
            )
            take_snapshot(store_with_pipeline, "p1", snap_dir)
        snaps = list_snapshots(snap_dir, "p1")
        assert len(snaps) == 5
