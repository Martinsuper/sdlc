"""Eval dataset loading (M-D2).

Datasets are JSONL — one EvalCase per line — so they diff cleanly in git and
can be appended to incrementally (from maintainer curation, regression capture,
or adversarial cases). Bad lines are skipped with a captured error rather than
aborting a whole run.
"""

from __future__ import annotations

import json
from pathlib import Path

from sdlc.eval.models import EvalCase


def load_cases(path: Path) -> list[EvalCase]:
    """Load EvalCases from a JSONL file. Silently skips blank lines; raises
    ValueError only if the file is missing."""
    if not path.exists():
        raise ValueError(f"Dataset not found: {path}")
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue  # tolerate a malformed line rather than failing the set
        if not isinstance(data, dict) or "id" not in data or "stage" not in data:
            continue
        cases.append(
            EvalCase(
                id=str(data["id"]),
                stage=str(data["stage"]),
                input=str(data.get("input", "")),
                context=data.get("context", {}) or {},
                ideal=data.get("ideal", {}) or {},
                source=str(data.get("source", "maintainer")),
            )
        )
    return cases


def load_dir(directory: Path, stage: str | None = None) -> list[EvalCase]:
    """Load all *.jsonl datasets under a directory, optionally filtered to one
    stage."""
    cases: list[EvalCase] = []
    if not directory.exists():
        return cases
    for f in sorted(directory.glob("*.jsonl")):
        cases.extend(load_cases(f))
    if stage:
        cases = [c for c in cases if c.stage == stage]
    return cases


def builtin_datasets_dir() -> Path:
    """Path to the datasets shipped with sdlc."""
    import sdlc

    return Path(sdlc.__file__).parent / "eval" / "datasets"
