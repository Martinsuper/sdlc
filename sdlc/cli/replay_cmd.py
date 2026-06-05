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
    summary = store.load_pipeline(pipeline_id)
    if not summary:
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    click.echo(f"Replaying pipeline: {pipeline_id}")
    click.echo(f"  Original status: {summary.status}")
    click.echo(f"  Stages: {summary.done_count}/{summary.stage_count}")
    if stage:
        click.echo(f"  From stage: {stage}")
    if fresh:
        click.echo("  Fresh mode: ignoring previous results")
    click.echo("Pipeline replay requires LLM integration (M2).")
