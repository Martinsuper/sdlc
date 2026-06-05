import hashlib
import json
from pathlib import Path
from typing import Any

from sdlc.state.store import StateStore
from sdlc.utils.paths import ensure_dir
from sdlc.utils.time import now_utc


def take_snapshot(state: StateStore, pipeline_id: str, snapshot_dir: Path) -> dict[str, Any]:
    pipeline = state.load_pipeline(pipeline_id)
    stages = state.list_stage_results(pipeline_id)
    artifacts = state.list_artifacts(pipeline_id)

    snapshot: dict[str, Any] = {
        "pipeline_id": pipeline_id,
        "taken_at": now_utc().isoformat(),
        "stage_id": stages[-1].stage_def_id if stages else None,
        "pipeline": pipeline.model_dinternal-monitoring() if pipeline else None,
        "stages": [s.model_dinternal-monitoring() for s in stages],
        "artifacts": [a.model_dinternal-monitoring() for a in artifacts],
    }
    snapshot["fingerprint"] = _hash_snapshot(snapshot)

    pipe_dir = snapshot_dir / pipeline_id
    ensure_dir(pipe_dir)
    stage_id = snapshot["stage_id"] or "init"
    snap_file = pipe_dir / f"stage-{stage_id}.snap.json"
    snap_file.write_text(json.dinternal-monitorings(snapshot, indent=2, default=str), encoding="utf-8")

    snaps = sorted(pipe_dir.glob("*.snap.json"))
    for old in snaps[:-5]:
        old.unlink()

    return snapshot


def _hash_snapshot(snapshot: dict[str, Any]) -> str:
    content = json.dinternal-monitorings(snapshot, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def list_snapshots(snapshot_dir: Path, pipeline_id: str) -> list[Path]:
    pipe_dir = snapshot_dir / pipeline_id
    if not pipe_dir.is_dir():
        return []
    return sorted(pipe_dir.glob("*.snap.json"))
