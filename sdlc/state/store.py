import hmac
import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sdlc.state.models import (
    Artifact,
    CostStat,
    KBDelta,
    PipelineSummary,
    ResumeState,
    StageResult,
)
from sdlc.state.schema import SCHEMA_SQL, VALID_TRANSITIONS
from sdlc.utils.paths import ensure_dir
from sdlc.utils.time import now_utc


class InvalidStateTransitionError(Exception):
    pass


class StateStore:
    def __init__(self, db_path: Path) -> None:
        ensure_dir(db_path.parent)
        self.db_path = db_path
        self.db = sqlite3.connect(
            str(db_path),
            isolation_level=None,
            check_same_thread=False,
        )
        self.db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.executescript(SCHEMA_SQL)
        self.db.execute("PRAGMA journal_mode=WAL")
        self._migrate_success_to_completed()

    def _migrate_success_to_completed(self) -> None:
        # Legacy rows used "SUCCESS" as the terminal state; the state machine
        # now uses "COMPLETED". Idempotent: only matches un-migrated rows.
        self.db.execute("UPDATE pipelines SET status='COMPLETED' WHERE status='SUCCESS'")
        self.db.execute("UPDATE stages SET status='COMPLETED' WHERE status='SUCCESS'")

    def _read_execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a read query under the lock for thread safety."""
        with self._lock:
            return self.db.execute(sql, params)

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        with self._lock:
            try:
                self.db.execute("BEGIN IMMEDIATE")
                yield self.db
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def save_pipeline(
        self,
        pipeline_id: str,
        entry_kind: str,
        profile_id: str,
        status: str = "NEW",
        meta_json: str = "{}",
    ) -> None:
        now = now_utc().isoformat()
        with self.transaction() as tx:
            tx.execute(
                "INSERT OR REPLACE INTO pipelines "
                "(id, entry_kind, profile_id, status, created_at, updated_at, meta_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (pipeline_id, entry_kind, profile_id, status, now, now, meta_json),
            )

    def load_pipeline(self, pipeline_id: str) -> PipelineSummary | None:
        row = self._read_execute(
            "SELECT * FROM v_pipeline_summary WHERE id=?", (pipeline_id,)
        ).fetchone()
        if not row:
            return None
        return PipelineSummary(**dict(row))

    def update_pipeline_status(self, pipeline_id: str, status: str, **updates: Any) -> None:
        now = now_utc().isoformat()
        with self.transaction() as tx:
            row = tx.execute(
                "SELECT status FROM pipelines WHERE id=?", (pipeline_id,)
            ).fetchone()
            if row:
                current_status = row["status"]
                if (
                    status not in VALID_TRANSITIONS.get(current_status, {status})
                    and current_status != status
                ):
                    raise InvalidStateTransitionError(
                        f"Invalid transition: {current_status} -> {status}"
                    )
            tx.execute(
                "UPDATE pipelines SET status=?, updated_at=? WHERE id=?",
                (status, now, pipeline_id),
            )

    def list_pipelines(
        self,
        status: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PipelineSummary]:
        query = "SELECT * FROM v_pipeline_summary WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status=?"
            params.append(status)
        if since:
            query += " AND created_at>=?"
            params.append(since.isoformat())
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self._read_execute(query, tuple(params)).fetchall()
        return [PipelineSummary(**dict(r)) for r in rows]

    def delete_pipeline(self, pipeline_id: str) -> None:
        with self.transaction() as tx:
            tx.execute("DELETE FROM pipelines WHERE id=?", (pipeline_id,))

    def save_stage_result(self, result: StageResult) -> None:
        with self.transaction() as tx:
            tx.execute(
                "INSERT OR REPLACE INTO stages "
                "(id, pipeline_id, stage_def_id, status, started_at, finished_at, error) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    result.id,
                    result.pipeline_id,
                    result.stage_def_id,
                    result.status,
                    result.started_at,
                    result.finished_at,
                    result.error,
                ),
            )

    def load_stage_result(self, pipeline_id: str, stage_id: str) -> StageResult | None:
        row = self._read_execute(
            "SELECT * FROM stages WHERE id=? AND pipeline_id=?",
            (stage_id, pipeline_id),
        ).fetchone()
        if not row:
            return None
        return StageResult(**dict(row))

    def list_stage_results(self, pipeline_id: str) -> list[StageResult]:
        rows = self._read_execute(
            "SELECT * FROM stages WHERE pipeline_id=? ORDER BY started_at",
            (pipeline_id,),
        ).fetchall()
        return [StageResult(**dict(r)) for r in rows]

    def register_artifact(self, artifact: Artifact) -> None:
        with self.transaction() as tx:
            tx.execute(
                "INSERT OR REPLACE INTO artifacts "
                "(id, pipeline_id, stage_id, type, path, content_hash, meta_json, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    artifact.id,
                    artifact.pipeline_id,
                    artifact.stage_id,
                    artifact.type,
                    artifact.path,
                    artifact.content_hash,
                    artifact.meta_json,
                    artifact.created_at,
                ),
            )

    def list_artifacts(self, pipeline_id: str, type: str | None = None) -> list[Artifact]:
        if type:
            rows = self._read_execute(
                "SELECT * FROM artifacts WHERE pipeline_id=? AND type=?",
                (pipeline_id, type),
            ).fetchall()
        else:
            rows = self._read_execute(
                "SELECT * FROM artifacts WHERE pipeline_id=?", (pipeline_id,)
            ).fetchall()
        return [Artifact(**dict(r)) for r in rows]

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        row = self._read_execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
        if not row:
            return None
        return Artifact(**dict(row))

    def record_llm_call(
        self,
        pipeline_id: str,
        stage_id: str | None,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        duration_ms: int,
        cached: bool,
    ) -> None:
        now = now_utc().isoformat()
        with self.transaction() as tx:
            tx.execute(
                "INSERT INTO llm_calls "
                "(pipeline_id, stage_id, model, input_tokens, output_tokens, "
                "cost_usd, duration_ms, cached, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    pipeline_id,
                    stage_id,
                    model,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    duration_ms,
                    int(cached),
                    now,
                ),
            )

    def get_pipeline_cost(self, pipeline_id: str) -> float:
        row = self._read_execute(
            "SELECT COALESCE(SUM(cost_usd), 0) as total FROM llm_calls WHERE pipeline_id=?",
            (pipeline_id,),
        ).fetchone()
        return float(row["total"]) if row else 0.0

    def get_cost_daily(self, since: datetime) -> list[CostStat]:
        rows = self._read_execute(
            "SELECT * FROM v_cost_daily WHERE day>=? ORDER BY day",
            (since.strftime("%Y-%m-%d"),),
        ).fetchall()
        return [CostStat(**dict(r)) for r in rows]

    def record_kb_delta(
        self,
        pipeline_id: str,
        stage_id: str | None,
        target: str,
        operation: str,
        fingerprint: str,
    ) -> int:
        now = now_utc().isoformat()
        with self.transaction() as tx:
            cursor = tx.execute(
                "INSERT INTO kb_deltas "
                "(pipeline_id, stage_id, target, operation, fingerprint, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (pipeline_id, stage_id, target, operation, fingerprint, now),
            )
            return cursor.lastrowid  # type: ignore

    def get_kb_deltas(self, target: str, since: datetime) -> list[KBDelta]:
        rows = self._read_execute(
            "SELECT * FROM kb_deltas WHERE target=? AND created_at>=? ORDER BY created_at",
            (target, since.isoformat()),
        ).fetchall()
        return [KBDelta(**dict(r)) for r in rows]

    def save_resume_token(self, pipeline_id: str, token: str, expires_at: str) -> None:
        # Normalize expires_at to UTC ISO format with timezone info
        dt = datetime.fromisoformat(expires_at)
        dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
        expires_utc = dt.isoformat()
        with self.transaction() as tx:
            tx.execute(
                "INSERT OR REPLACE INTO resume_tokens "
                "(pipeline_id, token, expires_at) VALUES (?,?,?)",
                (pipeline_id, token, expires_utc),
            )

    def verify_resume_token(self, pipeline_id: str, token: str) -> bool:
        row = self._read_execute(
            "SELECT token, expires_at FROM resume_tokens WHERE pipeline_id=?",
            (pipeline_id,),
        ).fetchone()
        if not row:
            return False
        if not hmac.compare_digest(row["token"], token):
            return False
        expires = datetime.fromisoformat(row["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return not datetime.now(UTC) > expires

    def get_resume_state(self, pipeline_id: str) -> ResumeState | None:
        row = self._read_execute(
            "SELECT * FROM resume_tokens WHERE pipeline_id=?", (pipeline_id,)
        ).fetchone()
        if not row:
            return None
        return ResumeState(
            pipeline_id=row["pipeline_id"],
            token=row["token"],
            expires_at=row["expires_at"],
        )

    def backup(self, dest: Path) -> None:
        ensure_dir(dest.parent)
        backup_db = sqlite3.connect(str(dest))
        with self._lock:
            self.db.backup(backup_db)
        backup_db.close()

    def restore(self, src: Path) -> None:
        src_db = sqlite3.connect(str(src))
        with self._lock:
            src_db.backup(self.db)
        src_db.close()
