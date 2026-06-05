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
    click.echo(f"TODO: implement run | input={input} profile={profile} severity={severity}")
