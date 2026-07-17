"""Tests for M-D3 cross-version regression (baseline snapshot + compare gate)."""

from __future__ import annotations

from sdlc.eval.baseline import Baseline, BaselineStore
from sdlc.eval.models import EvalReport, EvalResult, Score
from sdlc.eval.regression import compare


def _report(stage_scores: dict[str, float]) -> EvalReport:
    """Build a report with one result per (stage, score)."""
    results = []
    for i, (stage, score) in enumerate(stage_scores.items()):
        results.append(
            EvalResult(
                case_id=f"c{i}",
                stage=stage,
                score=Score(overall=score),
                passed=score >= 0.7,
            )
        )
    return EvalReport(results=results)


# --------------------------------------------------------------------------- #
# Baseline store
# --------------------------------------------------------------------------- #

def test_baseline_from_report_and_roundtrip(tmp_path):
    report = _report({"design": 0.8, "cr": 0.6})
    base = Baseline.from_report("v1.0", report)
    assert base.per_stage_mean == {"design": 0.8, "cr": 0.6}

    store = BaselineStore(tmp_path)
    store.save(base)
    loaded = store.load("v1.0")
    assert loaded is not None
    assert loaded.per_stage_mean["design"] == 0.8
    assert "v1.0" in store.list_versions()


def test_baseline_load_missing_returns_none(tmp_path):
    assert BaselineStore(tmp_path).load("nope") is None


# --------------------------------------------------------------------------- #
# Regression compare
# --------------------------------------------------------------------------- #

def test_no_regression_passes():
    base = Baseline.from_report("v1", _report({"design": 0.8, "cr": 0.6}))
    current = _report({"design": 0.82, "cr": 0.6})
    rep = compare(base, current, "v2")
    assert rep.passed
    assert rep.regressed == []


def test_regression_blocks():
    base = Baseline.from_report("v1", _report({"design": 0.8, "cr": 0.6}))
    current = _report({"design": 0.6, "cr": 0.6})  # design dropped 0.2
    rep = compare(base, current, "v2")
    assert not rep.passed
    assert rep.regressed == ["design"]
    assert rep.per_stage_delta["design"] < 0


def test_small_drop_within_threshold_passes():
    base = Baseline.from_report("v1", _report({"design": 0.80}))
    current = _report({"design": 0.77})  # -0.03, within default -0.05
    rep = compare(base, current, "v2")
    assert rep.passed


def test_improvement_flagged():
    base = Baseline.from_report("v1", _report({"design": 0.6}))
    current = _report({"design": 0.9})
    rep = compare(base, current, "v2")
    assert rep.improved == ["design"]
    assert rep.passed


def test_new_stage_ignored():
    base = Baseline.from_report("v1", _report({"design": 0.8}))
    current = _report({"design": 0.8, "newstage": 0.1})
    rep = compare(base, current, "v2")
    # A stage not in the baseline can't regress — nothing to compare against.
    assert rep.passed
    assert "newstage" not in rep.per_stage_delta


def test_custom_threshold():
    base = Baseline.from_report("v1", _report({"design": 0.8}))
    current = _report({"design": 0.75})  # -0.05
    strict = compare(base, current, "v2", threshold=-0.01)
    assert not strict.passed
    lenient = compare(base, current, "v2", threshold=-0.10)
    assert lenient.passed
