import click


@click.command()
@click.argument("pipeline_id")
@click.option("--token", help="Resume token")
@click.option("--from-stage", help="Force restart from stage")
@click.option("--reset-gates", is_flag=True)
@click.option("--force", is_flag=True)
def resume(pipeline_id, token, from_stage, reset_gates, force):
    """Resume a paused/failed pipeline."""
    click.echo(f"TODO: implement resume | pipeline_id={pipeline_id}")
