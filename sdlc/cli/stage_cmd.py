import click


@click.group()
def stage():
    """Browse pipeline stages."""


@stage.command("list")
@click.option("--category", default=None, help="Filter by category")
def stage_list(category):
    """List all stages."""
    from sdlc.stage.catalog import StageCatalog

    catalog = StageCatalog()
    stages = catalog.list_stages()
    if category:
        stages = [s for s in stages if s.category == category]
    if not stages:
        click.echo("No stages found")
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Pipeline Stages")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Category", style="green")
    table.add_column("Subagent", style="yellow")
    table.add_column("Timeout", justify="right")

    for s in stages:
        table.add_row(s.id, s.name, s.category, s.subagent, f"{s.timeout}s")
    console.print(table)


@stage.command("show")
@click.argument("stage_id")
def stage_show(stage_id):
    """Show stage details."""
    from sdlc.stage.catalog import StageCatalog, StageNotFoundError

    catalog = StageCatalog()
    try:
        s = catalog.get(stage_id)
    except StageNotFoundError:
        click.echo(f"Stage not found: {stage_id}", err=True)
        raise SystemExit(1) from None

    click.echo(f"ID:          {s.id}")
    click.echo(f"Name:        {s.name}")
    click.echo(f"Category:    {s.category}")
    click.echo(f"Subagent:    {s.subagent}")
    click.echo(f"Timeout:     {s.timeout}s")
    click.echo(f"Max Retries: {s.max_retries}")
    if s.required_artifacts:
        click.echo(f"Required:    {', '.join(s.required_artifacts)}")
    if s.produces_artifacts:
        click.echo(f"Produces:    {', '.join(s.produces_artifacts)}")
    if s.pre_kb_load:
        click.echo(f"KB Load:     {', '.join(s.pre_kb_load)}")
