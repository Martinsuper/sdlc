"""Eval data model (M-D2): cases, per-dimension scores, and results.

The Score dimensions deliberately mirror the M-A2 reflect criteria
(correctness / completeness / rule-compliance / kb-alignment) so a single
acceptance-criteria + Rule vocabulary drives both in-loop reflection and
out-of-loop evaluation — define the bar once, use it in both places.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalCase:
    """One evaluation example: an input and the ideal it should satisfy."""

    id: str
    stage: str
    input: str
    context: dict[str, Any] = field(default_factory=dict)
    # ideal.criteria: the acceptance criteria the produced artifact must meet.
    ideal: dict[str, Any] = field(default_factory=dict)
    source: str = "maintainer"  # maintainer | regression | adversarial

    @property
    def criteria(self) -> list[str]:
        return [str(c) for c in (self.ideal.get("criteria") or [])]


@dataclass
class Score:
    """A judged score across dimensions, each 0..1."""

    correctness: float = 0.0
    completeness: float = 0.0
    rule_compliance: float = 0.0
    kb_alignment: float = 0.0
    overall: float = 0.0
    rationale: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "correctness": self.correctness,
            "completeness": self.completeness,
            "rule_compliance": self.rule_compliance,
            "kb_alignment": self.kb_alignment,
            "overall": self.overall,
            "rationale": self.rationale,
        }


@dataclass
class EvalResult:
    """The outcome of scoring one case."""

    case_id: str
    stage: str
    score: Score
    passed: bool
    produced: str = ""


@dataclass
class EvalReport:
    """Aggregate over a run: mean overall, pass rate, per-stage breakdown."""

    results: list[EvalResult] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def mean_overall(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score.overall for r in self.results) / len(self.results)

    def by_stage(self) -> dict[str, dict[str, float]]:
        stages: dict[str, list[EvalResult]] = {}
        for r in self.results:
            stages.setdefault(r.stage, []).append(r)
        out: dict[str, dict[str, float]] = {}
        for stage, rs in stages.items():
            out[stage] = {
                "count": float(len(rs)),
                "pass_rate": sum(1 for r in rs if r.passed) / len(rs),
                "mean_overall": sum(r.score.overall for r in rs) / len(rs),
            }
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "pass_rate": self.pass_rate,
            "mean_overall": self.mean_overall,
            "by_stage": self.by_stage(),
            "results": [
                {
                    "case_id": r.case_id,
                    "stage": r.stage,
                    "passed": r.passed,
                    "score": r.score.as_dict(),
                }
                for r in self.results
            ],
        }
