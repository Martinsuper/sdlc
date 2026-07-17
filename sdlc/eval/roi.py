"""ROI quantification (M-D4).

CostTracker records the cost side (LLM spend, now non-zero for custom gateways
after the pricing fallback); this module adds the benefit side — time saved,
defect reduction, release acceleration — so a team can report what sdlc is
worth, not just what it costs.

Human baselines are hard to calibrate absolutely, so the design says: teams
self-calibrate, we ship default templates, and we report *relative* trends
rather than chasing absolute precision. ROI numbers are shareable after
anonymization.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Default human baselines (minutes) per stage category — a starting template
# teams override with their own calibration. Deliberately conservative.
DEFAULT_HUMAN_BASELINE_MIN: dict[str, float] = {
    "requirements": 60.0,
    "design": 180.0,
    "impl": 240.0,
    "test": 120.0,
    "cr": 60.0,
    "docs": 45.0,
    "deploy": 30.0,
}

# Assumed cost of a person-hour, for converting saved time into money. Teams
# override; used only for the (relative) money-saved figure.
DEFAULT_HOURLY_RATE_USD = 75.0


@dataclass
class StageTiming:
    stage: str
    category: str
    agent_minutes: float


@dataclass
class ROIInputs:
    """What a team feeds in for one pipeline (or an aggregate window)."""

    timings: list[StageTiming] = field(default_factory=list)
    llm_cost_usd: float = 0.0
    gate_minutes: float = 0.0  # human approval time
    defects_before: float | None = None  # escaped defects without sdlc
    defects_after: float | None = None  # escaped defects with sdlc
    cycle_days_before: float | None = None  # requirement→prod, before
    cycle_days_after: float | None = None  # requirement→prod, after
    human_baseline_min: dict[str, float] = field(default_factory=dict)
    hourly_rate_usd: float = DEFAULT_HOURLY_RATE_USD


@dataclass
class ROIReport:
    time_saved_min: float
    money_saved_usd: float
    total_cost_usd: float
    net_value_usd: float
    roi_ratio: float | None  # net_value / total_cost; None when cost is 0
    defect_reduction_pct: float | None
    release_speedup_pct: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "time_saved_min": round(self.time_saved_min, 1),
            "money_saved_usd": round(self.money_saved_usd, 2),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "net_value_usd": round(self.net_value_usd, 2),
            "roi_ratio": round(self.roi_ratio, 2) if self.roi_ratio is not None else None,
            "defect_reduction_pct": (
                round(self.defect_reduction_pct, 1)
                if self.defect_reduction_pct is not None
                else None
            ),
            "release_speedup_pct": (
                round(self.release_speedup_pct, 1)
                if self.release_speedup_pct is not None
                else None
            ),
        }


def _pct_reduction(before: float | None, after: float | None) -> float | None:
    """Percent reduction from before→after, or None if not measurable."""
    if before is None or after is None or before <= 0:
        return None
    return (before - after) / before * 100.0


def compute_roi(inputs: ROIInputs) -> ROIReport:
    """Compute an ROI report from timings, cost, and optional outcome deltas.

    Time saved = sum over stages of (human baseline − agent time), floored at 0
    per stage (a stage slower than baseline contributes 0, not negative — we
    don't claim the agent "cost" time it merely spent). Money saved converts
    saved minutes at the hourly rate. Cost includes LLM spend plus human gate
    time valued at the same rate."""
    baseline = {**DEFAULT_HUMAN_BASELINE_MIN, **inputs.human_baseline_min}

    time_saved = 0.0
    for t in inputs.timings:
        human = baseline.get(t.category, 0.0)
        time_saved += max(0.0, human - t.agent_minutes)

    rate_per_min = inputs.hourly_rate_usd / 60.0
    money_saved = time_saved * rate_per_min
    gate_cost = inputs.gate_minutes * rate_per_min
    total_cost = inputs.llm_cost_usd + gate_cost
    net_value = money_saved - total_cost
    roi_ratio = (net_value / total_cost) if total_cost > 0 else None

    return ROIReport(
        time_saved_min=time_saved,
        money_saved_usd=money_saved,
        total_cost_usd=total_cost,
        net_value_usd=net_value,
        roi_ratio=roi_ratio,
        defect_reduction_pct=_pct_reduction(inputs.defects_before, inputs.defects_after),
        release_speedup_pct=_pct_reduction(inputs.cycle_days_before, inputs.cycle_days_after),
    )
