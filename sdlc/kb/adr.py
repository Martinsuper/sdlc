"""ADR store with effect-weighted learning (M-A6).

Architecture Decision Records are stored as JSONL under the KB. Beyond the
usual decision/context, each ADR carries an *outcome* and an *effect_score*
(-1..1) written back by the feedback loop (M-D5): positive = good post-deploy
outcome, negative = incident/rollback. Agents then consume decisions ranked by
effect_score so high-scoring decisions are injected first and low-scoring
anti-patterns are surfaced as things to avoid.

Safety valves:
  - sample_count gate: a decision's score only influences ranking once it has
    accumulated enough samples, so a single noisy signal can't drive behavior.
  - the loop must be validated by cross-version regression (M-D3) — effect
    weighting is applied, but "did it actually improve" is proven separately.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# A decision must reach this many samples before its effect_score changes how
# it is ranked/injected (noise guard from the design).
MIN_SAMPLES_FOR_EFFECT = 3


@dataclass
class ADR:
    id: str
    decision: str
    context: str = ""
    made_by_agent: str = ""
    made_at: str = ""
    outcome: str = ""  # post-deploy effect description, written by M-D5
    effect_score: float = 0.0  # -1..1; positive good, negative incident/rollback
    sample_count: int = 0  # signals accumulated; gates effect influence

    @property
    def effect_active(self) -> bool:
        """Whether this ADR has enough samples for its score to matter."""
        return self.sample_count >= MIN_SAMPLES_FOR_EFFECT

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ADRStore:
    """JSONL-backed ADR store under <kb_root>/adr/records.jsonl."""

    def __init__(self, kb_root: Path) -> None:
        self.kb_root = kb_root
        self.path = kb_root / "adr" / "records.jsonl"

    def _load_all(self) -> list[ADR]:
        if not self.path.exists():
            return []
        out: list[ADR] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            out.append(ADR(**{k: d.get(k) for k in ADR.__dataclass_fields__ if k in d}))
        return out

    def _write_all(self, adrs: list[ADR]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            "\n".join(json.dinternal-monitorings(a.as_dict(), ensure_ascii=False) for a in adrs) + "\n"
            if adrs
            else "",
            encoding="utf-8",
        )
        tmp.rename(self.path)

    def record(self, adr: ADR) -> None:
        """Insert or replace an ADR by id."""
        adrs = [a for a in self._load_all() if a.id != adr.id]
        adrs.append(adr)
        self._write_all(adrs)

    def get(self, adr_id: str) -> ADR | None:
        return next((a for a in self._load_all() if a.id == adr_id), None)

    def all(self) -> list[ADR]:
        return self._load_all()

    def update_outcome(
        self, adr_id: str, outcome: str, effect_delta: float
    ) -> ADR | None:
        """Record a post-deploy signal for an ADR (used by M-D5 feedback).

        Accumulates one sample and folds effect_delta into a running mean, so a
        single incident weighs against several no-consequence signals over time
        rather than being overwritten."""
        adrs = self._load_all()
        target = next((a for a in adrs if a.id == adr_id), None)
        if target is None:
            return None
        n = target.sample_count
        # Running mean so repeated signals converge; clamp to [-1, 1].
        target.effect_score = max(
            -1.0, min(1.0, (target.effect_score * n + effect_delta) / (n + 1))
        )
        target.sample_count = n + 1
        target.outcome = outcome or target.outcome
        self._write_all(adrs)
        return target

    def ranked_for_injection(self, limit: int = 10) -> tuple[list[ADR], list[ADR]]:
        """Return (preferred, avoid) decisions for context injection.

        Only ADRs whose effect is active (enough samples) are split by score:
        positive → preferred (inject first), negative → avoid (anti-patterns).
        Score-inactive ADRs are treated neutrally and omitted from both lists,
        so behavior degrades to the pre-feedback baseline until evidence
        accumulates."""
        active = [a for a in self._load_all() if a.effect_active]
        preferred = sorted(
            (a for a in active if a.effect_score > 0),
            key=lambda a: a.effect_score,
            reverse=True,
        )[:limit]
        avoid = sorted(
            (a for a in active if a.effect_score < 0), key=lambda a: a.effect_score
        )[:limit]
        return preferred, avoid
