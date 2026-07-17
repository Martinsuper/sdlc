"""`sdlc plugin` — scaffold, validate, and pack sdlc extension plugins (M-C1)."""

from __future__ import annotations

import pathlib

import click

from sdlc.plugin.manifest import PLUGIN_TYPES


@click.group()
def plugin() -> None:
    """Author sdlc extension plugins (adapter/profile/stage/rule-set/etc.)."""


@plugin.command("new")
@click.argument("plugin_type", type=click.Choice(sorted(PLUGIN_TYPES)))
@click.argument("name")
@click.option("--dest", default=".", help="Directory to create the plugin under.")
@click.option("--author", default="", help="Plugin author.")
def plugin_new(plugin_type: str, name: str, dest: str, author: str) -> None:
    """Scaffold a new plugin skeleton."""
    from sdlc.plugin.scaffold import scaffold

    try:
        plugin_dir = scaffold(plugin_type, name, pathlib.Path(dest), author=author)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    click.echo(f"Created {plugin_type} plugin at {plugin_dir}")
    click.echo(f"  edit {plugin_dir / 'plugin.yaml'}, then `sdlc plugin validate {plugin_dir}`")


@plugin.command("validate")
@click.argument("plugin_dir", default=".")
def plugin_validate(plugin_dir: str) -> None:
    """Validate a plugin directory."""
    from sdlc.plugin.validator import PluginValidator

    report = PluginValidator().validate(pathlib.Path(plugin_dir))
    for w in report.warnings:
        click.echo(f"  warning: {w}", err=True)
    if report.ok:
        click.echo("Plugin is valid.")
        return
    click.echo("Plugin is INVALID:", err=True)
    for e in report.errors:
        click.echo(f"  error: {e}", err=True)
    raise SystemExit(1)


@plugin.command("test")
@click.argument("plugin_dir", default=".")
def plugin_test(plugin_dir: str) -> None:
    """Dry-run a plugin: validate, then confirm its entry YAML loads."""
    from sdlc.plugin.validator import PluginValidator

    pd = pathlib.Path(plugin_dir)
    report = PluginValidator().validate(pd)
    if not report.ok:
        click.echo("Plugin failed validation; fix errors before testing:", err=True)
        for e in report.errors:
            click.echo(f"  error: {e}", err=True)
        raise SystemExit(1)
    click.echo("Plugin validates and its entry loads. Ready to pack.")


@plugin.command("pack")
@click.argument("plugin_dir", default=".")
@click.option("--out", default=None, help="Output directory for the .sdlcpkg.")
def plugin_pack(plugin_dir: str, out: str | None) -> None:
    """Validate and pack a plugin into a .sdlcpkg archive."""
    from sdlc.plugin.packer import pack

    try:
        archive = pack(
            pathlib.Path(plugin_dir), pathlib.Path(out) if out else None
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None
    click.echo(f"Packed: {archive}")
