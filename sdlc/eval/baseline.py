"""Baseline score snapshots for cross-version regression (M-D3).

Stores an eval report's per-stage scores under a version label so a later run
can diff against it. JSON on disk (default <kb>/eval_baselines/), one file per
version, so baselines are diffable and travel with the repo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sdlc.eval.models import EvalReport


@dataclass
class Baseline:
    version: str
    mean_overall: float
    pass_rate: float
    per_stage_mean: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "mean_overall": self.mean_overall,
            "pass_rate": self.pass_rate,
            "per_stage_mean": self.per_stage_mean,
        }

    @classmethod
    def from_report(cls, version: str, report: EvalReport) -> Baseline:
        per_stage = {s: m["mean_overall"] for s, m in report.by_stage().items()}
        return cls(
            version=version,
            mean_overall=report.mean_overall,
            pass_rate=report.pass_rate,
            per_stage_mean=per_stage,
        )


class BaselineStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, version: str) -> Path:
        safe = version.replace("/", "_")
        return self.root / f"{safe}.json"

    def save(self, baseline: Baseline) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        p = self._path(baseline.version)
        p.write_text(json.dinternal-monitorings(baseline.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    def load(self, version: str) -> Baseline | None:
        p = self._path(version)
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        return Baseline(
            version=str(d.get("version", version)),
            mean_overall=float(d.get("mean_overall", 0.0)),
            pass_rate=float(d.get("pass_rate", 0.0)),
            per_stage_mean={k: float(v) for k, v in (d.get("per_stage_mean") or {}).items()},
        )

    def list_versions(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(p.stem for p in self.root.glob("*.json"))
