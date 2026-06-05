import click


@click.command()
@click.argument("path", default=".")
@click.option("--depth", type=int, default=5)
@click.option("--no-llm", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--template", type=click.Choice(["default", "empty", "full"]), default="default")
@click.option("--adapter", help="Force adapter")
@click.option("--no-commit", is_flag=True)
@click.option("-i", "--interactive", is_flag=True)
def init(path, depth, no_llm, force, template, adapter, no_commit, interactive):
    """Initialize project for sdlc."""
    click.echo(f"TODO: implement init | path={path} depth={depth}")
