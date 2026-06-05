import click

from sdlc import __version__


@click.command()
def version():
    """Show version."""
    import sys

    click.echo(
        f"sdlc {__version__} "
        f"(python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})"
    )
