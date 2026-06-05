import click


@click.command()
@click.option("--since", default="7d", help="Lookback period")
@click.option("--by-model", is_flag=True)
@click.option("--by-stage", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def stats(since, by_model, by_stage, as_json):
    click.echo("TODO: implement stats")
