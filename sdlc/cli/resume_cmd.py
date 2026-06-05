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
    summary = store.load_pipeline(pipeline_id)
    if not summary:
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    # Verify resume token if provided
    if token and not store.verify_resume_token(pipeline_id, token):
        click.echo("Invalid or expired resume token.", err=True)
        raise SystemExit(1)

    click.echo(f"Resuming pipeline: {pipeline_id}")
    click.echo(f"  Status: {summary.status}")
    click.echo(f"  Stages done: {summary.done_count}/{summary.stage_count}")
    if from_stage:
        click.echo(f"  From stage: {from_stage}")
    if reset_gates:
        click.echo("  Gates will be reset")
    click.echo("Pipeline resume requires LLM integration (M2).")
