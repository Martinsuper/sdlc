"""Agent-output evaluation framework (M-D2).

Measures produced-artifact *quality* (does the agent's output meet its
acceptance criteria?), complementing the unit/integration tests that measure
code *correctness*. Built on a JSONL dataset, an LLM-as-judge, and a runner
that aggregates per-stage scores.
"""

from sdlc.eval.baseline import Baseline, BaselineStore
from sdlc.eval.dataset import builtin_datasets_dir, load_cases, load_dir
from sdlc.eval.judge import Judge
from sdlc.eval.models import EvalCase, EvalReport, EvalResult, Score
from sdlc.eval.regression import RegressionReport, compare
from sdlc.eval.runner import EvalRunner

__all__ = [
    "Baseline",
    "BaselineStore",
    "EvalCase",
    "EvalReport",
    "EvalResult",
    "EvalRunner",
    "Judge",
    "RegressionReport",
    "Score",
    "builtin_datasets_dir",
    "compare",
    "load_cases",
    "load_dir",
]
