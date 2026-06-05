import click


@click.group()
def adapter():
    """Browse technology adapters."""


@adapter.command("list")
def adapter_list():
    """List all adapters."""
    from sdlc.adapter.dongboot import register_dongboot
    from sdlc.adapter.registry import AdapterRegistry

    registry = AdapterRegistry()
    register_dongboot(registry)
    adapters = registry.list_adapters()

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Adapters")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Version", style="green")
    table.add_column("Components", justify="right")
    table.add_column("Enforce Rules")

    for a in adapters:
        table.add_row(
            a.id,
            a.name,
            a.version,
            str(len(a.components)),
            "✓" if a.enforce_rules else "✗",
        )
    console.print(table)


@adapter.command("show")
@click.argument("adapter_id")
def adapter_show(adapter_id):
    """Show adapter details."""
    from sdlc.adapter.dongboot import register_dongboot
    from sdlc.adapter.registry import AdapterNotFoundError, AdapterRegistry

    registry = AdapterRegistry()
    register_dongboot(registry)
    try:
        a = registry.get(adapter_id)
    except AdapterNotFoundError:
        click.echo(f"Adapter not found: {adapter_id}", err=True)
        raise SystemExit(1) from None

    click.echo(f"ID:            {a.id}")
    click.echo(f"Name:          {a.name}")
    click.echo(f"Version:       {a.version}")
    click.echo(f"Enforce Rules: {'Yes' if a.enforce_rules else 'No'}")
    click.echo(f"Rule Sets:     {', '.join(a.rule_sets) if a.rule_sets else 'None'}")
    click.echo(f"\nComponents ({len(a.components)}):")
    for c in a.components:
        click.echo(
            f"  - {c.id} ({c.type}) detect={c.detect} "
            f"enforce={'Yes' if c.enforce else 'No'}"
        )
    click.echo(f"\nDetect Patterns ({len(a.detect_patterns)}):")
    for p in a.detect_patterns:
        click.echo(f"  - {p}")


@adapter.command("detect")
@click.argument("path", default=".", type=click.Path(exists=True))
def adapter_detect(path):
    """Detect adapters for a project."""
    from pathlib import Path

    from sdlc.adapter.detector import AdapterDetector
    from sdlc.adapter.dongboot import register_dongboot
    from sdlc.adapter.registry import AdapterRegistry

    registry = AdapterRegistry()
    register_dongboot(registry)
    detector = AdapterDetector(registry)
    detected = detector.detect(Path(path))
    if detected:
        for a in detected:
            click.echo(f"  ✓ {a.id} — {a.name}")
    else:
        click.echo("No adapters detected")
