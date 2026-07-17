"""Eval runner (M-D2): score cases and aggregate into a report.

The runner is producer-agnostic. Callers pass a ``produce`` coroutine that maps
a case to a produced artifact string (e.g. run the real stage, or replay a
stored artifact for regression). The runner judges each produced artifact and
aggregates the scores. ``pass_threshold`` decides pass/fail on the overall
score.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sdlc.eval.judge import Judge
from sdlc.eval.models import EvalCase, EvalReport, EvalResult

Producer = Callable[[EvalCase], Awaitable[str]]


class EvalRunner:
    def __init__(self, judge: Judge, pass_threshold: float = 0.7) -> None:
        self.judge = judge
        self.pass_threshold = pass_threshold

    async def run(
        self,
        cases: list[EvalCase],
        produce: Producer,
        rules_for: Callable[[EvalCase], list[dict[str, Any]]] | None = None,
    ) -> EvalReport:
        results: list[EvalResult] = []
        for case in cases:
            produced = await produce(case)
            rules = rules_for(case) if rules_for is not None else []
            score = await self.judge.score(case, produced, case.criteria, rules)
            results.append(
                EvalResult(
                    case_id=case.id,
                    stage=case.stage,
                    score=score,
                    passed=score.overall >= self.pass_threshold,
                    produced=produced,
                )
            )
        return EvalReport(results=results)
