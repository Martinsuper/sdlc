import click


@click.group()
def kb():
    """Manage knowledge base."""


@kb.command("list")
def kb_list():
    click.echo("TODO: implement kb list")


@kb.command("show")
@click.argument("path")
def kb_show(path):
    click.echo(f"TODO: implement kb show | path={path}")


@kb.command("diff")
@click.argument("path1")
@click.argument("path2")
def kb_diff(path1, path2):
    click.echo(f"TODO: implement kb diff | {path1} vs {path2}")


@kb.command("scan")
@click.option("--full", is_flag=True, help="Full scan (not incremental)")
def kb_scan(full):
    click.echo(f"TODO: implement kb scan | full={full}")


@kb.command("update")
@click.option("--stage", help="Trigger update for specific stage")
def kb_update(stage):
    click.echo(f"TODO: implement kb update | stage={stage}")


@kb.command("stats")
def kb_stats():
    click.echo("TODO: implement kb stats")


@kb.command("reconcile")
def kb_reconcile():
    click.echo("TODO: implement kb reconcile")
