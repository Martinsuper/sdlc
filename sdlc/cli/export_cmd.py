import click


@click.command()
@click.argument("pipeline_id")
@click.option("--format", "fmt", type=click.Choice(["json", "yaml", "markdown"]), default="json")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export(pipeline_id, fmt, output):
    click.echo(f"TODO: implement export | pipeline_id={pipeline_id}")
