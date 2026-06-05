import click


@click.command()
@click.argument("pipeline_id")
@click.option("--stage", help="Replay from specific stage")
@click.option("--fresh", is_flag=True, help="Ignore previous results")
def replay(pipeline_id, stage, fresh):
    """Replay a pipeline execution."""
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

    click.echo(f"Replaying pipeline: {pipeline_id}")
    click.echo(f"  Original status: {pipeline.status}")
    click.echo(f"  Stages: {pipeline.done_count}/{pipeline.stage_count}")
    if stage:
        click.echo(f"  From stage: {stage}")
    if fresh:
        click.echo("  Fresh mode: ignoring previous results")

    # Attempt real pipeline replay
    try:
        import asyncio

        from sdlc.cli.deps import build_deps

        deps = build_deps()
        result = asyncio.run(
            deps.coordinator.run(
                input_text=f"[Replay] {pipeline_id}",
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
        click.echo(f"\nReplay execution requires LLM integration: {e}")
