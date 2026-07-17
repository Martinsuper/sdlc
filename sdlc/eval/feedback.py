"""Feedback loop: post-deploy/human signals → decision effect scores (M-D5).

Turns outcome signals into an effect_score written back onto the ADR that
drove the decision, closing the loop M-A6 consumes. Signal weighting follows
the design: an incident/rollback weighs more than a no-consequence approval, so
one production incident outweighs several uneventful passes.

The loop's *correctness* (did weighting actually improve output, vs. reinforce
a bias?) is proven separately by cross-version regression (M-D3); this module
only produces the signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sdlc.kb.adr import ADR, ADRStore

# Signal → effect delta in [-1, 1]. Negative signals (incident, rollback,
# rejection) are weighted more heavily than positive ones, so harm outweighs
# routine success.
_SIGNAL_WEIGHTS: dict[str, float] = {
    "deploy_success": 0.3,
    "adopted": 0.5,
    "gate_approved": 0.2,
    "gate_rejected": -0.5,
    "cr_issue": -0.4,
    "error_rate_up": -0.7,
    "rollback": -1.0,
    "incident": -1.0,
}


@dataclass
class Signal:
    """One attributable outcome signal for a decision."""

    adr_id: str
    kind: str  # a key in _SIGNAL_WEIGHTS
    note: str = ""


@dataclass
class FeedbackReport:
    updated: list[str] = field(default_factory=list)
    unknown_adrs: list[str] = field(default_factory=list)
    unknown_signals: list[str] = field(default_factory=list)


class FeedbackRecorder:
    def __init__(self, kb_root: Path) -> None:
        self.store = ADRStore(kb_root)

    def effect_delta(self, kind: str) -> float | None:
        return _SIGNAL_WEIGHTS.get(kind)

    def record_signal(self, signal: Signal) -> ADR | None:
        """Apply one signal to its ADR. Returns the updated ADR, or None if the
        signal kind is unknown or the ADR does not exist."""
        delta = self.effect_delta(signal.kind)
        if delta is None:
            return None
        return self.store.update_outcome(signal.adr_id, signal.note or signal.kind, delta)

    def record_batch(self, signals: list[Signal]) -> FeedbackReport:
        report = FeedbackReport()
        for s in signals:
            if self.effect_delta(s.kind) is None:
                report.unknown_signals.append(s.kind)
                continue
            updated = self.record_signal(s)
            if updated is None:
                report.unknown_adrs.append(s.adr_id)
            else:
                report.updated.append(s.adr_id)
        return report
