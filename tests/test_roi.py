"""Tests for M-D4 ROI quantification."""

from __future__ import annotations

from sdlc.eval.roi import ROIInputs, StageTiming, compute_roi


def test_time_saved_vs_baseline():
    # design baseline 180 min, agent took 30 => 150 saved.
    inputs = ROIInputs(timings=[StageTiming("s1", "design", 30.0)])
    r = compute_roi(inputs)
    assert r.time_saved_min == 150.0


def test_slower_than_baseline_floors_at_zero():
    # A stage slower than the human baseline contributes 0, not negative.
    inputs = ROIInputs(timings=[StageTiming("s1", "docs", 100.0)])  # baseline 45
    r = compute_roi(inputs)
    assert r.time_saved_min == 0.0


def test_money_saved_and_roi_ratio():
    inputs = ROIInputs(
        timings=[StageTiming("s1", "impl", 60.0)],  # baseline 240 => 180 saved
        llm_cost_usd=1.0,
        hourly_rate_usd=60.0,  # $1/min
    )
    r = compute_roi(inputs)
    assert r.money_saved_usd == 180.0  # 180 min * $1/min
    assert r.total_cost_usd == 1.0
    assert r.net_value_usd == 179.0
    assert r.roi_ratio == 179.0


def test_roi_ratio_none_when_no_cost():
    r = compute_roi(ROIInputs(timings=[StageTiming("s1", "design", 30.0)]))
    assert r.total_cost_usd == 0.0
    assert r.roi_ratio is None


def test_gate_time_counted_as_cost():
    inputs = ROIInputs(
        timings=[StageTiming("s1", "cr", 10.0)],  # baseline 60 => 50 saved
        gate_minutes=30.0,
        hourly_rate_usd=60.0,
    )
    r = compute_roi(inputs)
    assert r.total_cost_usd == 30.0  # 30 gate min * $1/min


def test_defect_and_release_deltas():
    inputs = ROIInputs(
        timings=[],
        defects_before=10.0,
        defects_after=6.0,
        cycle_days_before=20.0,
        cycle_days_after=15.0,
    )
    r = compute_roi(inputs)
    assert r.defect_reduction_pct == 40.0
    assert r.release_speedup_pct == 25.0


def test_deltas_none_when_missing():
    r = compute_roi(ROIInputs(timings=[]))
    assert r.defect_reduction_pct is None
    assert r.release_speedup_pct is None


def test_custom_baseline_override():
    inputs = ROIInputs(
        timings=[StageTiming("s1", "design", 30.0)],
        human_baseline_min={"design": 300.0},  # override 180 -> 300
    )
    r = compute_roi(inputs)
    assert r.time_saved_min == 270.0


def test_as_dict_rounds():
    r = compute_roi(ROIInputs(timings=[StageTiming("s1", "impl", 33.3)], llm_cost_usd=0.12345))
    d = r.as_dict()
    assert d["total_cost_usd"] == 0.1235 or d["total_cost_usd"] == 0.1234
