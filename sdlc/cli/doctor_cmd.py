import click


@click.command()
@click.option("--check-llm/--no-check-llm", default=True, help="Probe LLM connectivity with a real request")
def doctor(check_llm: bool):
    """Run diagnostics."""
    import shutil
    import sys
    from pathlib import Path

    from sdlc.utils.paths import sdlc_home

    # Each check: (name, status) where status is "pass" | "warn" | "fail".
    checks: list[tuple[str, str]] = []

    def _b(ok: bool) -> str:
        return "pass" if ok else "fail"

    # Python >= 3.11
    checks.append(("Python >= 3.11", _b(sys.version_info >= (3, 11))))

    # uv installed
    checks.append(("uv installed", _b(shutil.which("uv") is not None)))

    # Config dir writable
    home = sdlc_home()
    checks.append(("~/.sdlc exists", _b(home.exists())))

    # Disk space > 1GB
    usage = shutil.disk_usage(home.parent if home.exists() else Path.home())
    checks.append(("Disk space >= 1GB", _b(usage.free >= 1024**3)))

    # LLM connectivity — real request. This is informational and never fails
    # doctor's exit code (doctor must stay deterministic for CI and offline use):
    # reachable => pass, otherwise => warn with the reason.
    if check_llm:
        try:
            from sdlc.llm.smoke import smoke_test
            from sdlc.utils.config_loader import load_config

            cfg = load_config()
            ok, detail = smoke_test(cfg.llm, timeout=20.0)
            if ok:
                checks.append((f"LLM reachable — {detail}", "pass"))
            elif detail.startswith("API key not set"):
                checks.append((f"LLM connectivity ({detail}; set the key to enable)", "warn"))
            else:
                checks.append((f"LLM unreachable — {detail}", "warn"))
        except Exception as e:
            checks.append((f"LLM check error — {e}", "warn"))

    marks = {"pass": "✓", "warn": "!", "fail": "✗"}
    has_fail = False
    for name, status in checks:
        click.echo(f"  {marks[status]} {name}")
        if status == "fail":
            has_fail = True

    if has_fail:
        click.echo("\nSome checks failed", err=True)
        raise SystemExit(1)
    click.echo("\nAll checks passed")
