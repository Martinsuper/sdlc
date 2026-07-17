"""`sdlc eval` — run agent-output quality evaluation (M-D2).

- ``sdlc eval list``   : show datasets/cases discovered (no model needed)
- ``sdlc eval run``    : judge produced artifacts and print an aggregate report

``run`` needs a reachable judge model. Without one it exits with a clear message
rather than pretending to score, so the command can't report a fake baseline.
"""

from __future__ import annotations

import json

import click


@click.group()
def eval_group() -> None:
    """Evaluate agent output quality (datasets + LLM-as-judge)."""


@eval_group.command("list")
@click.option("--stage", default=None, help="Filter to one stage id.")
def eval_list(stage: str | None) -> None:
    """List discovered eval cases (no model required)."""
    from sdlc.eval.dataset import builtin_datasets_dir, load_dir

    cases = load_dir(builtin_datasets_dir(), stage=stage)
    if not cases:
        click.echo("No eval cases found.")
        return
    by_stage: dict[str, int] = {}
    for c in cases:
        by_stage[c.stage] = by_stage.get(c.stage, 0) + 1
    click.echo(f"Discovered {len(cases)} case(s):")
    for s, n in sorted(by_stage.items()):
        click.echo(f"  {s:20s} {n}")


@eval_group.command("run")
@click.option("--stage", default=None, help="Filter to one stage id.")
@click.option("--judge-model", default="", help="Override the judge model.")
@click.option("--threshold", type=float, default=0.7, help="Pass threshold on overall score.")
@click.option("--json", "as_json", is_flag=True, help="Emit the report as JSON.")
def eval_run(stage: str | None, judge_model: str, threshold: float, as_json: bool) -> None:
    """Judge produced artifacts against acceptance criteria and report."""
    import asyncio

    from sdlc.eval.dataset import builtin_datasets_dir, load_dir
    from sdlc.eval.judge import Judge
    from sdlc.eval.models import EvalCase
    from sdlc.eval.runner import EvalRunner
    from sdlc.llm.smoke import smoke_test
    from sdlc.utils.config_loader import load_config

    cases = load_dir(builtin_datasets_dir(), stage=stage)
    if not cases:
        click.echo("No eval cases found.")
        return

    cfg = load_config()
    ok, detail = smoke_test(cfg.llm, timeout=20.0)
    if not ok:
        click.echo(f"Judge model not reachable ({detail}).", err=True)
        click.echo("Configure an LLM to run eval; `sdlc eval list` works offline.", err=True)
        raise SystemExit(2)

    from sdlc.cli.deps import build_llm_client

    llm = build_llm_client(cfg)
    judge = Judge(llm, judge_model=judge_model)
    runner = EvalRunner(judge, pass_threshold=threshold)

    # Default producer: without a stage-execution harness here, evaluate the
    # ideal-criteria echo as a placeholder produced artifact. Real stage
    # production is wired by callers/CI that pass their own producer.
    async def _produce(case: EvalCase) -> str:
        return case.context.get("produced", "") or ""

    report = asyncio.run(runner.run(cases, _produce))

    if as_json:
        click.echo(json.dinternal-monitorings(report.as_dict(), ensure_ascii=False, indent=2))
        return

    click.echo(f"Eval report: {report.count} case(s)")
    click.echo(f"  pass rate:    {report.pass_rate:.0%}")
    click.echo(f"  mean overall: {report.mean_overall:.2f}")
    click.echo("  by stage:")
    for s, m in sorted(report.by_stage().items()):
        click.echo(
            f"    {s:16s} n={int(m['count'])} pass={m['pass_rate']:.0%} "
            f"mean={m['mean_overall']:.2f}"
        )
