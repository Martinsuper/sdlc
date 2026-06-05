import click


@click.command()
@click.option("--list", "list_profiles", is_flag=True)
@click.option("--show", help="Show profile details")
def profile(list_profiles, show):
    click.echo("TODO: implement profile")
