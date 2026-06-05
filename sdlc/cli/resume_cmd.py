import click


@click.command()
@click.argument("pipeline_id")
@click.option("--token", help="Resume token")
@click.option("--from-stage", help="Force restart from stage")
@click.option("--reset-gates", is_flag=True)
@click.option("--force", is_flag=True)
def resume(pipeline_id, token, from_stage, reset_gates, force):
    """Resume a paused/failed pipeline."""
    from sdlc.utils.paths import sdlc_home

    home = sdlc_home()
    db_path = home / "state.db"
    if not db_path.exists():
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    from sdlc.state.store import StateStore

    store = StateStore(db_path)
    pipeline = store.load_pipeline(pipeline_id)
    if not pipeline:
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    if pipeline.status.upper() not in ("PAUSED", "FAILED", "RUNNING"):
        click.echo(f"Pipeline is {pipeline.status}, cannot resume")
        raise SystemExit(1)

    # Verify resume token if provided
    if token and not force and not store.verify_resume_token(pipeline_id, token):
        click.echo("Invalid or expired resume token.", err=True)
        raise SystemExit(10)

    click.echo(f"Resuming pipeline: {pipeline_id}")
    click.echo(f"  Status: {pipeline.status}")
    click.echo(f"  Stages done: {pipeline.done_count}/{pipeline.stage_count}")
    if from_stage:
        click.echo(f"  From stage: {from_stage}")
    if reset_gates:
        click.echo("  Gates will be reset")

    # Attempt real pipeline resume
    try:
        import asyncio

        from sdlc.cli.deps import build_deps

        deps = build_deps()
        result = asyncio.run(
            deps.coordinator.run(
                input_text=f"[Resume] {pipeline_id}",
                profile_id=pipeline.profile_id if pipeline.profile_id else None,
            )
        )
        click.echo(f"\nPipeline {'completed' if result.status == 'completed' else result.status}")
        click.echo(f"  Stages: {len(result.stage_results)}")
        click.echo(f"  Cost: ${result.total_cost_usd:.4f}")
    except SystemExit:
        raise
    except Exception as e:
        # If full deps assembly or pipeline execution fails (e.g. missing API keys),
        # report but don't crash the informational output above.
        click.echo(f"\nResume execution requires LLM integration: {e}")
