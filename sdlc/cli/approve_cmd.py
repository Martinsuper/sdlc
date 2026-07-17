"""`sdlc approve` / `sdlc reject` — resolve a manual-review gate (M-B1).

A pipeline suspended at a MANUAL_REVIEW gate (status WAITING_APPROVAL) can be
released — or rejected — from the CLI without a server, keeping "CLI works
standalone" intact. Approving resumes the pipeline; rejecting fails it.
"""

from __future__ import annotations

import getpass

import click


def _resolve_and_maybe_resume(pipeline_id: str, gate_id: str, approved: bool, reason: str) -> None:
    import asyncio

    from sdlc.state.store import StateStore
    from sdlc.utils.paths import sdlc_home

    db_path = sdlc_home() / "state.db"
    if not db_path.exists():
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    store = StateStore(db_path)
    summary = store.load_pipeline(pipeline_id)
    if summary is None:
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    try:
        reviewer = getpass.getuser()
    except Exception:
        reviewer = "unknown"

    ok = store.resolve_waiting(
        pipeline_id,
        "approval",
        gate_id,
        answer={"approved": approved, "reason": reason, "reviewer": reviewer},
    )
    if not ok:
        click.echo(
            f"No pending approval for gate '{gate_id}' on pipeline {pipeline_id}.",
            err=True,
        )
        raise SystemExit(1)

    verb = "approved" if approved else "rejected"
    click.echo(f"Gate '{gate_id}' {verb} by {reviewer}.")

    # Drive resume through the coordinator. If full deps can't be assembled
    # (e.g. no LLM configured), the decision is still persisted above.
    try:
        from sdlc.cli.deps import build_deps

        deps = build_deps()
        result = asyncio.run(deps.coordinator.resume_from_waiting(pipeline_id))
        click.echo(f"Pipeline {result.status}.")
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Decision recorded; resume requires LLM integration: {e}")


@click.command()
@click.argument("pipeline_id")
@click.argument("gate_id")
@click.option("--reason", default="", help="Optional approval note.")
def approve(pipeline_id: str, gate_id: str, reason: str) -> None:
    """Approve a suspended manual-review gate and resume the pipeline."""
    _resolve_and_maybe_resume(pipeline_id, gate_id, approved=True, reason=reason)


@click.command()
@click.argument("pipeline_id")
@click.argument("gate_id")
@click.option("--reason", default="", help="Rejection reason.")
def reject(pipeline_id: str, gate_id: str, reason: str) -> None:
    """Reject a suspended manual-review gate; the pipeline fails."""
    _resolve_and_maybe_resume(pipeline_id, gate_id, approved=False, reason=reason)
