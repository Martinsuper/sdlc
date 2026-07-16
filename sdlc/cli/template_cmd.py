"""`sdlc template` — locate or print bundled design/release templates.

Portable replacement for hardcoded absolute template paths in slash commands.
The `sdlc` console script always resolves to the installed package, so this
reliably points at the right template regardless of the caller's cwd.
"""

from __future__ import annotations

import pathlib

import click

_TEMPLATES = {
    "backend-design": "builtin/templates/backend-design.md",
    "release-checklist": "builtin/templates/release-checklist.md",
}


def _templates_dir() -> pathlib.Path:
    import sdlc

    return pathlib.Path(sdlc.__file__).parent


@click.command()
@click.argument("name", required=False, type=click.Choice(sorted(_TEMPLATES)))
@click.option("--path", "show_path", is_flag=True, help="Print the resolved file path instead of contents")
def template(name: str | None, show_path: bool) -> None:
    """Locate or print a bundled template (backend-design | release-checklist)."""
    base = _templates_dir()
    if not name:
        click.echo("Available templates:")
        for key, rel in sorted(_TEMPLATES.items()):
            click.echo(f"  {key:20} {base / rel}")
        return

    tpl = base / _TEMPLATES[name]
    if not tpl.is_file():
        raise click.ClickException(f"Template file not found: {tpl}")
    if show_path:
        click.echo(str(tpl))
    else:
        click.echo(tpl.read_text(encoding="utf-8"))
