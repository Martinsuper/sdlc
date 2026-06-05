import click


@click.command()
@click.option("--list", "list_adapters", is_flag=True)
@click.option("--show", help="Show adapter details")
def adapter(list_adapters, show):
    click.echo("TODO: implement adapter")
