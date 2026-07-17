"""`sdlc answer` — answer a subagent's clarification question (M-A3).

A pipeline suspended at ``ask_user`` (status WAITING_CLARIFICATION) is resumed
by supplying the answer here — no server required. The answer is injected into
the run context so the subagent's ask_user returns it instead of re-suspending.
"""

from __future__ import annotations

import click


@click.command()
@click.argument("pipeline_id")
@click.option("--question-id", "-q", required=True, help="Question id from the suspension.")
@click.option("--answer", "-a", "answer_text", required=True, help="The answer to inject.")
def answer(pipeline_id: str, question_id: str, answer_text: str) -> None:
    """Answer a pending clarification and resume the pipeline."""
    import asyncio

    from sdlc.state.store import StateStore
    from sdlc.utils.paths import sdlc_home

    db_path = sdlc_home() / "state.db"
    if not db_path.exists():
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    store = StateStore(db_path)
    if store.load_pipeline(pipeline_id) is None:
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    ok = store.resolve_waiting(
        pipeline_id, "clarification", question_id, answer={"answer": answer_text}
    )
    if not ok:
        click.echo(
            f"No pending clarification '{question_id}' on pipeline {pipeline_id}.",
            err=True,
        )
        raise SystemExit(1)
    click.echo(f"Answer recorded for {question_id}.")

    try:
        from sdlc.cli.deps import build_deps

        deps = build_deps()
        result = asyncio.run(deps.coordinator.resume_from_waiting(pipeline_id))
        click.echo(f"Pipeline {result.status}.")
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Answer recorded; resume requires LLM integration: {e}")
