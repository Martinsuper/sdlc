import click


@click.command()
@click.option("--list", "list_stages", is_flag=True, help="List all stages")
@click.option("--show", help="Show stage details")
def stage(list_stages, show):
    click.echo("TODO: implement stage")
