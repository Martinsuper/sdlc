import click


@click.command()
@click.argument("pipeline_id")
@click.option("--stage", help="Replay from specific stage")
@click.option("--mock-llm", is_flag=True)
def replay(pipeline_id, stage, mock_llm):
    click.echo(f"TODO: implement replay | pipeline_id={pipeline_id}")
