import click


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["json", "yaml"]), default="json")
def import_cmd(path, fmt):
    click.echo(f"TODO: implement import | path={path}")
