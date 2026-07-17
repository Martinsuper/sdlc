"""Cross-version regression gate (M-D3).

Compares a current eval report against a saved baseline and blocks release if
any stage's mean score dropped more than a threshold. This is the quality
gatekeeper for agent changes (pillar 1) and marketplace extensions (pillar 3):
any change must prove it did not make output worse.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sdlc.eval.baseline import Baseline
from sdlc.eval.models import EvalReport


@dataclass
class RegressionReport:
    baseline_version: str
    current_version: str
    per_stage_delta: dict[str, float] = field(default_factory=dict)
    regressed: list[str] = field(default_factory=list)  # stages that dropped past threshold
    improved: list[str] = field(default_factory=list)
    passed: bool = True
    threshold: float = -0.05

    def summary(self) -> str:
        verdict = "PASS" if self.passed else "REGRESSION"
        return (
            f"[{verdict}] {self.current_version} vs {self.baseline_version} "
            f"(threshold {self.threshold:+.2f}); regressed={self.regressed or 'none'}"
        )


def compare(
    baseline: Baseline,
    current: EvalReport,
    current_version: str,
    threshold: float = -0.05,
) -> RegressionReport:
    """Diff current per-stage scores against the baseline.

    A stage regresses when its mean score dropped by more than |threshold|.
    Stages absent from the baseline are ignored (nothing to compare). Any
    regression flips passed to False so a release gate can block."""
    current_by_stage = {s: m["mean_overall"] for s, m in current.by_stage().items()}
    per_stage_delta: dict[str, float] = {}
    regressed: list[str] = []
    improved: list[str] = []

    for stage, base_score in baseline.per_stage_mean.items():
        if stage not in current_by_stage:
            continue
        delta = current_by_stage[stage] - base_score
        per_stage_delta[stage] = delta
        if delta < threshold:
            regressed.append(stage)
        elif delta > abs(threshold):
            improved.append(stage)

    return RegressionReport(
        baseline_version=baseline.version,
        current_version=current_version,
        per_stage_delta=per_stage_delta,
        regressed=sorted(regressed),
        improved=sorted(improved),
        passed=not regressed,
        threshold=threshold,
    )
