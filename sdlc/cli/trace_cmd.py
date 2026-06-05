import click


@click.command()
@click.argument("pipeline_id")
@click.option("--stage", help="Filter by stage")
@click.option("--type", "event_type", help="Filter by event type")
@click.option("--since", help="Since timespec")
@click.option("--json", "as_json", is_flag=True)
@click.option("--follow", is_flag=True)
def trace(pipeline_id, stage, event_type, since, as_json, follow):
    """Trace pipeline execution."""
    from sdlc.audit.logger import AuditLogger
    from sdlc.utils.paths import sdlc_home

    home = sdlc_home()
    audit_path = home / "audit.jsonl"
    if not audit_path.exists():
        click.echo(f"No audit log found for pipeline: {pipeline_id}", err=True)
        raise SystemExit(1)

    audit = AuditLogger(audit_path)
    events = list(audit.query(pipeline_id=pipeline_id, event_type=event_type))

    if not events:
        click.echo(f"No events found for pipeline: {pipeline_id}")
        return

    if as_json:
        import json

        click.echo(json.dinternal-monitorings(events, indent=2, default=str))
    else:
        for evt in events:
            ts = evt.get("ts", "?")
            typ = evt.get("type", "?")
            payload = evt.get("payload", {})
            click.echo(f"  [{ts}] {typ}: {payload}")
