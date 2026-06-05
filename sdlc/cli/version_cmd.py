import click

from sdlc import __version__


@click.command()
def version():
    """Show version."""
    click.echo(f"sdlc {__version__}")
