import click


@click.command()
def doctor():
    """Run diagnostics."""
    import shutil
    import sys
    from pathlib import Path

    from sdlc.utils.paths import sdlc_home

    checks: list[tuple[str, bool]] = []

    # Python >= 3.11
    checks.append(("Python >= 3.11", sys.version_info >= (3, 11)))

    # uv installed
    checks.append(("uv installed", shutil.which("uv") is not None))

    # Config dir writable
    home = sdlc_home()
    checks.append(("~/.sdlc exists", home.exists()))

    # Disk space > 1GB
    usage = shutil.disk_usage(home.parent if home.exists() else Path.home())
    checks.append(("Disk space >= 1GB", usage.free >= 1024**3))

    all_pass = True
    for name, ok in checks:
        mark = "✓" if ok else "✗"
        click.echo(f"  {mark} {name}")
        if not ok:
            all_pass = False

    if all_pass:
        click.echo("\nAll checks passed")
    else:
        click.echo("\nSome checks failed", err=True)
        raise SystemExit(1)
