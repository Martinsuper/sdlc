import click


@click.command()
@click.argument("input", required=False)
@click.option("-p", "--profile", default="auto", help="Force Profile")
@click.option(
    "-e",
    "--entry-kind",
    type=click.Choice(
        [
            "idea",
            "feature",
            "bug",
            "hotfix",
            "refactor",
            "test",
            "infra",
            "release",
            "revert",
            "doc",
            "migrate",
            "audit",
        ]
    ),
    help="Force EntryKind",
)
@click.option("-a", "--adapter", help="Force Adapter")
@click.option("-s", "--stages", help="Only run specified stages (comma-separated)")
@click.option("--skip-stages", help="Skip stages")
@click.option("--severity", type=click.Choice(["P0", "P1", "P2", "P3"]), help="Force severity")
@click.option("--gate-mode", type=click.Choice(["auto", "manual", "skip"]), default="auto")
@click.option("--no-deploy", is_flag=True)
@click.option("--no-monitor", is_flag=True)
@click.option("--no-kb-update", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--resume-on-fail", is_flag=True)
@click.option("--max-cost", type=float, default=5.0, help="Cost limit in USD")
@click.option("--timeout", type=int, help="Global timeout in seconds")
@click.option("--tag", multiple=True, help="Custom tags KEY=VAL")
def run(
    input,
    profile,
    entry_kind,
    adapter,
    stages,
    skip_stages,
    severity,
    gate_mode,
    no_deploy,
    no_monitor,
    no_kb_update,
    dry_run,
    resume_on_fail,
    max_cost,
    timeout,
    tag,
):
    """Execute an SDLC pipeline."""
    import asyncio
    import sys
    from pathlib import Path

    from sdlc.core.entry_detector import EntryDetector
    from sdlc.core.models import EntryKind

    # Read input
    if not input:
        click.echo("Error: Please provide input (text, @file, or - for stdin)", err=True)
        raise SystemExit(1)

    raw_input = input
    if input.startswith("@"):
        path = Path(input[1:])
        if not path.exists():
            click.echo(f"File not found: {path}", err=True)
            raise SystemExit(1)
        raw_input = path.read_text()
    elif input == "-":
        raw_input = sys.stdin.read()

    # Detect entry kind
    detector = EntryDetector()
    entry = detector.detect(raw_input)

    # Override entry kind if specified
    if entry_kind:
        entry.kind = EntryKind(entry_kind)

    click.echo(f"Entry detected: {entry.kind.value}")
    click.echo(f"  Input: {raw_input[:80]}{'...' if len(raw_input) > 80 else ''}")
    click.echo(f"  Confidence: {entry.confidence:.2f}")
    click.echo(f"  Profile: {profile}")
    if severity:
        click.echo(f"  Severity: {severity}")
    if entry.detected_attachments:
        click.echo(f"  Attachments: {', '.join(entry.detected_attachments)}")

    if dry_run:
        click.echo("\nDry run mode -- pipeline plan generated but not executed")
        click.echo(f"  Stages would run based on profile '{profile}'")
        return

    click.echo("\nStarting SDLC pipeline...")

    try:
        from sdlc.cli.deps import build_deps

        deps = build_deps()
        # Override max cost if specified
        if max_cost:
            deps.cost_tracker.max_budget = max_cost

        result = asyncio.run(
            deps.coordinator.run(
                input_text=raw_input,
                profile_id=profile if profile != "auto" else None,
                adapter_id=adapter,
            )
        )

        click.echo(f"\nPipeline {'completed' if result.status == 'completed' else result.status}")
        click.echo(f"  Stages: {len(result.stage_results)}")
        click.echo(f"  Cost: ${result.total_cost_usd:.4f}")

    except KeyboardInterrupt:
        click.echo("\nPipeline interrupted by user")
        raise SystemExit(9) from None
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        raise SystemExit(1) from None
