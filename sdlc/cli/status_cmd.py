import click


@click.command()
@click.argument("pipeline_id", required=False)
@click.option("--all", "show_all", is_flag=True)
@click.option("--status", type=click.Choice(["running", "paused", "completed", "failed"]))
@click.option("--since", help="Since timespec (1d, 7d, ISO)")
@click.option("--limit", type=int, default=20)
@click.option("--json", "as_json", is_flag=True)
@click.option("--watch", is_flag=True)
def status(pipeline_id, show_all, status, since, limit, as_json, watch):
    """Show pipeline status."""
    from sdlc.utils.paths import sdlc_home

    home = sdlc_home()
    db_path = home / "state.db"

    if not db_path.exists():
        click.echo("No pipelines found. Run 'sdlc run' to start a pipeline.")
        return

    from sdlc.state.store import StateStore

    store = StateStore(db_path)

    if pipeline_id:
        summary = store.load_pipeline(pipeline_id)
        if not summary:
            click.echo(f"Pipeline not found: {pipeline_id}", err=True)
            raise SystemExit(1)
        if as_json:
            import json

            click.echo(json.dinternal-monitorings(summary.model_dinternal-monitoring(), indent=2, default=str))
        else:
            click.echo(f"Pipeline:     {summary.id}")
            click.echo(f"Status:       {summary.status}")
            click.echo(f"Entry Kind:   {summary.entry_kind}")
            click.echo(f"Profile:      {summary.profile_id}")
            click.echo(f"Created:      {summary.created_at}")
            click.echo(f"Stages:       {summary.done_count}/{summary.stage_count}")
            click.echo(f"Cost:         ${summary.total_cost:.2f}")
    else:
        pipelines = store.list_pipelines(status=status)
        if not pipelines:
            click.echo("No pipelines found.")
            return
        if as_json:
            import json

            click.echo(json.dinternal-monitorings([p.model_dinternal-monitoring() for p in pipelines[:limit]], indent=2, default=str))
        else:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="Pipelines")
            table.add_column("ID", style="cyan")
            table.add_column("Entry", style="white")
            table.add_column("Profile", style="green")
            table.add_column("Status")
            table.add_column("Cost", justify="right")
            table.add_column("Stages", justify="right")
            for p in pipelines[:limit]:
                status_str = p.status
                if status_str == "completed":
                    status_display = f"[green]{status_str}[/green]"
                elif status_str == "failed":
                    status_display = f"[red]{status_str}[/red]"
                elif status_str == "running":
                    status_display = f"[yellow]{status_str}[/yellow]"
                else:
                    status_display = status_str
                table.add_row(
                    p.id,
                    p.entry_kind,
                    p.profile_id,
                    status_display,
                    f"${p.total_cost:.2f}",
                    f"{p.done_count}/{p.stage_count}",
                )
            console.print(table)
