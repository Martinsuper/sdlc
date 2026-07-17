"""Tests for the M-D2 eval framework (sdlc/eval/).

The judge is exercised with a stubbed LLM client (canned score JSON), so these
run with no network and no API key — the property the earlier agent attempt
missed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from sdlc.eval.dataset import builtin_datasets_dir, load_cases, load_dir
from sdlc.eval.judge import Judge
from sdlc.eval.models import EvalCase, EvalReport
from sdlc.eval.runner import EvalRunner


def _case(cid: str = "c1", stage: str = "design") -> EvalCase:
    return EvalCase(id=cid, stage=stage, input="do x", ideal={"criteria": ["a", "b"]})


class _StubLLM:
    """LLM whose complete() returns a fixed judge JSON — no API needed."""

    def __init__(self, payload: str) -> None:
        self.payload = payload

    async def complete(self, req):
        block = MagicMock()
        block.type = "text"
        block.text = self.payload
        resp = MagicMock()
        resp.content = [block]
        resp.cost_usd = 0.0
        return resp


# --------------------------------------------------------------------------- #
# Dataset
# --------------------------------------------------------------------------- #

def test_builtin_dataset_loads():
    cases = load_dir(builtin_datasets_dir())
    assert cases, "builtin datasets should not be empty"
    assert all(c.id and c.stage for c in cases)


def test_load_cases_skips_bad_lines(tmp_path):
    f = tmp_path / "d.jsonl"
    f.write_text(
        '{"id":"g1","stage":"design","input":"x","ideal":{"criteria":["c"]}}\n'
        "not json\n"
        "\n"
        '{"missing":"id"}\n'
        '{"id":"g2","stage":"cr","input":"y"}\n',
        encoding="utf-8",
    )
    cases = load_cases(f)
    assert [c.id for c in cases] == ["g1", "g2"]


def test_load_dir_filters_by_stage():
    cr = load_dir(builtin_datasets_dir(), stage="cr")
    assert cr and all(c.stage == "cr" for c in cr)


# --------------------------------------------------------------------------- #
# Judge
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_judge_parses_dimensions():
    llm = _StubLLM(
        '{"correctness":0.9,"completeness":0.8,"rule_compliance":1.0,'
        '"kb_alignment":0.7,"overall":0.85,"rationale":"good"}'
    )
    score = await Judge(llm).score(_case(), "produced artifact")
    assert score.correctness == 0.9
    assert score.overall == 0.85
    assert score.rationale == "good"


@pytest.mark.asyncio
async def test_judge_clamps_out_of_range():
    llm = _StubLLM('{"correctness":2.0,"completeness":-1,"overall":5}')
    score = await Judge(llm).score(_case(), "x")
    assert score.correctness == 1.0
    assert score.completeness == 0.0
    assert score.overall == 1.0


@pytest.mark.asyncio
async def test_judge_unparseable_scores_zero():
    # A judge that can't answer must NOT certify quality.
    score = await Judge(_StubLLM("sorry, I cannot")).score(_case(), "x")
    assert score.overall == 0.0


@pytest.mark.asyncio
async def test_judge_derives_overall_when_missing():
    llm = _StubLLM(
        '{"correctness":1.0,"completeness":1.0,"rule_compliance":0.0,"kb_alignment":0.0}'
    )
    score = await Judge(llm).score(_case(), "x")
    assert score.overall == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# Runner + report
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_runner_aggregates_pass_and_fail():
    # Two cases: one high score (pass), one low (fail) at threshold 0.7.
    scores = iter([
        '{"correctness":0.9,"completeness":0.9,"rule_compliance":0.9,"kb_alignment":0.9,"overall":0.9}',
        '{"correctness":0.2,"completeness":0.2,"rule_compliance":0.2,"kb_alignment":0.2,"overall":0.2}',
    ])

    class _SeqLLM:
        async def complete(self, req):
            block = MagicMock()
            block.type = "text"
            block.text = next(scores)
            resp = MagicMock()
            resp.content = [block]
            resp.cost_usd = 0.0
            return resp

    runner = EvalRunner(Judge(_SeqLLM()), pass_threshold=0.7)
    cases = [_case("c1", "design"), _case("c2", "design")]

    async def _produce(case):
        return "artifact"

    report = await runner.run(cases, _produce)
    assert report.count == 2
    assert report.pass_rate == 0.5
    assert report.mean_overall == pytest.approx(0.55)
    assert "design" in report.by_stage()


def test_report_empty_is_safe():
    r = EvalReport()
    assert r.count == 0 and r.pass_rate == 0.0 and r.mean_overall == 0.0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def test_eval_list_cli_offline():
    from sdlc.cli.eval_cmd import eval_group

    result = CliRunner().invoke(eval_group, ["list"])
    assert result.exit_code == 0
    assert "case(s)" in result.output
