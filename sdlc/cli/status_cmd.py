import click


@click.command()
@click.argument("pipeline_id", required=False)
@click.option("--all", "show_all", is_flag=True)
@click.option("--status", type=click.Choice(["running", "paused", "completed", "failed"]))
@click.option("--since", help="Since timespec (1d, 7d, ISO)")
@click.option("--limit", type=int, default=20)
@click.option("--json", "as_json", is_flag=True)
@click.option("--watch", is_flag=True)
def status(pipeline_id, show_all, status, since, limit, as_json, watch):
    """Show pipeline status."""
    click.echo(f"TODO: implement status | pipeline_id={pipeline_id}")
