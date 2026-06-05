import click


@click.command()
def doctor():
    """Run diagnostics."""
    click.echo("All checks passed (stub)")
