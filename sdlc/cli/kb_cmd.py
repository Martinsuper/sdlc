"""kb_cmd — Knowledge base management CLI commands."""

import difflib
from pathlib import Path

import click

from sdlc.kb.knowledge_base import KBFileNotFoundError, KnowledgeBase
from sdlc.utils.paths import project_root


def _get_kb_root() -> Path:
    """Return the KB root directory, or exit if not found."""
    root = project_root() / "doc" / "kb"
    if not root.exists():
        click.echo("No KB found. Run 'sdlc init' first.", err=True)
        raise SystemExit(1)
    return root


@click.group()
def kb():
    """Manage knowledge base."""


@kb.command("list")
@click.option("--pattern", default="**/*", help="Glob pattern to filter")
def kb_list(pattern):
    """List KB files."""
    root = _get_kb_root()
    kbase = KnowledgeBase(root)
    layers = kbase.list_layers(pattern)
    if not layers:
        click.echo("No KB files found")
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Knowledge Base Files")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Size", justify="right")
    for layer in layers:
        table.add_row(layer.name, layer.type, f"{layer.size_bytes}B")
    console.print(table)


@kb.command("show")
@click.argument("path")
def kb_show(path):
    """Show KB file content."""
    root = _get_kb_root()
    kbase = KnowledgeBase(root)
    try:
        content = kbase.read_content(path)
        click.echo(content)
    except KBFileNotFoundError:
        click.echo(f"KB file not found: {path}", err=True)
        raise SystemExit(1) from None


@kb.command("diff")
@click.argument("path1")
@click.argument("path2")
def kb_diff(path1, path2):
    """Diff two KB files."""
    root = _get_kb_root()
    kbase = KnowledgeBase(root)
    try:
        c1 = kbase.read_content(path1).splitlines(keepends=True)
        c2 = kbase.read_content(path2).splitlines(keepends=True)
        diff = difflib.unified_diff(c1, c2, fromfile=path1, tofile=path2)
        output = "".join(diff)
        if output:
            click.echo(output)
        else:
            click.echo("Files are identical")
    except KBFileNotFoundError as e:
        click.echo(f"KB file not found: {e}", err=True)
        raise SystemExit(1) from None


@kb.command("scan")
@click.option("--full", is_flag=True, help="Full scan (not incremental)")
def kb_scan(full):
    """Scan project and update KB."""
    click.echo("KB scanning is not yet available (M2). Use 'sdlc init' to bootstrap KB.")


@kb.command("update")
@click.option("--stage", help="Trigger update for specific stage")
def kb_update(stage):
    """Manually trigger KB update."""
    click.echo(f"KB update triggered for stage: {stage or 'all'}")
    click.echo("Note: Full KB update requires a running pipeline context (M2).")


@kb.command("stats")
def kb_stats():
    """Show KB health statistics."""
    root = _get_kb_root()
    kbase = KnowledgeBase(root)
    layers = kbase.list_layers()
    total_size = sum(layer.size_bytes for layer in layers)
    click.echo(f"Files:      {len(layers)}")
    click.echo(f"Total Size: {total_size} bytes")
    types: dict[str, int] = {}
    for layer in layers:
        types[layer.type] = types.get(layer.type, 0) + 1
    for t, c in sorted(types.items()):
        click.echo(f"  {t}: {c}")


@kb.command("reconcile")
def kb_reconcile():
    """Run KB reconciliation."""
    click.echo("KB reconciliation is not yet available (M2).")
