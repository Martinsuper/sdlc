import click


@click.group()
def profile():
    """Browse project profiles."""


@profile.command("list")
def profile_list():
    """List all profiles."""
    from sdlc.profile.registry import ProfileRegistry, register_builtins

    registry = ProfileRegistry()
    register_builtins(registry)
    profiles = registry.list_profiles()

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Profiles")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Severity", style="yellow")
    table.add_column("Stages", justify="right")

    for p in profiles:
        table.add_row(p.id, p.name, p.severity, str(len(p.base_stages)))
    console.print(table)


@profile.command("show")
@click.argument("profile_id")
def profile_show(profile_id):
    """Show profile details."""
    from sdlc.profile.registry import ProfileNotFoundError, ProfileRegistry, register_builtins

    registry = ProfileRegistry()
    register_builtins(registry)
    try:
        p = registry.get(profile_id)
    except ProfileNotFoundError:
        click.echo(f"Profile not found: {profile_id}", err=True)
        raise SystemExit(1) from None

    click.echo(f"ID:            {p.id}")
    click.echo(f"Name:          {p.name}")
    click.echo(f"Severity:      {p.severity}")
    click.echo(f"Entry Kinds:   {', '.join(p.entry_kinds) if p.entry_kinds else 'Any'}")
    click.echo(f"Base Stages:   {', '.join(p.base_stages)}")
    if p.skip_stages:
        click.echo(f"Skip Stages:   {', '.join(p.skip_stages)}")
    if p.extra_stages:
        click.echo(f"Extra Stages:  {', '.join(p.extra_stages)}")
