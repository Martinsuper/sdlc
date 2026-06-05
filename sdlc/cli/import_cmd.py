import click


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["json", "yaml"]), default="json")
def import_cmd(path, fmt):
    """Import configuration or pipeline data."""
    import json
    from pathlib import Path

    target = Path(path)
    if fmt == "json":
        try:
            data = json.loads(target.read_text())
            click.echo(f"Imported from {path}")
            click.echo(f"  Type: {data.get('type', 'unknown')}")
            click.echo(f"  Data keys: {', '.join(str(k) for k in data)}")
            click.echo("Note: Full import requires running pipeline context (M2).")
        except json.JSONDecodeError:
            click.echo(f"Invalid JSON file: {path}", err=True)
            raise SystemExit(1) from None
    else:
        from sdlc.utils.yaml_io import load_yaml

        data = load_yaml(target)
        click.echo(f"Imported from {path}")
        if data and isinstance(data, dict):
            click.echo(f"  Type: {data.get('type', 'unknown')}")
            click.echo(f"  Data keys: {', '.join(str(k) for k in data)}")
        click.echo("Note: Full import requires running pipeline context (M2).")
