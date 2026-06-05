import click


@click.command()
@click.argument("pipeline_id")
@click.option("--stage", help="Filter by stage")
@click.option("--type", "event_type", help="Filter by event type")
@click.option("--since", help="Since timespec")
@click.option("--json", "as_json", is_flag=True)
@click.option("--follow", is_flag=True)
def trace(pipeline_id, stage, event_type, since, as_json, follow):
    """Trace pipeline execution."""
    click.echo(f"TODO: implement trace | pipeline_id={pipeline_id}")
