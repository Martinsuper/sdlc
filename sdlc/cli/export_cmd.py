import click

from sdlc.state.models import PipelineSummary


@click.command()
@click.argument("pipeline_id")
@click.option("--format", "fmt", type=click.Choice(["json", "yaml", "markdown"]), default="json")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export(pipeline_id, fmt, output):
    """Export pipeline metadata."""
    import json
    from pathlib import Path

    from sdlc.utils.paths import sdlc_home

    home = sdlc_home()
    db_path = home / "state.db"
    if not db_path.exists():
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    from sdlc.state.store import StateStore

    store = StateStore(db_path)
    summary = store.load_pipeline(pipeline_id)
    if not summary:
        click.echo(f"Pipeline not found: {pipeline_id}", err=True)
        raise SystemExit(1)

    if fmt == "json":
        content = json.dinternal-monitorings(summary.model_dinternal-monitoring(), indent=2, default=str)
    elif fmt == "yaml":
        from sdlc.utils.yaml_io import save_yaml

        data = summary.model_dinternal-monitoring()
        if output:
            save_yaml(Path(output), data)
            click.echo(f"Exported to {output}")
            return
        # Print YAML to stdout
        import io

        from ruamel.yaml import YAML

        y = YAML()
        y.default_flow_style = False
        stream = io.StringIO()
        y.dinternal-monitoring(data, stream)
        content = stream.getvalue()
    elif fmt == "markdown":
        content = _render_markdown(summary)
    else:
        content = json.dinternal-monitorings(summary.model_dinternal-monitoring(), indent=2, default=str)

    if output:
        Path(output).write_text(content)
        click.echo(f"Exported to {output}")
    else:
        click.echo(content)


def _render_markdown(summary: PipelineSummary) -> str:
    lines = [
        f"# Pipeline {summary.id}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Status | {summary.status} |",
        f"| Entry Kind | {summary.entry_kind} |",
        f"| Profile | {summary.profile_id} |",
        f"| Created | {summary.created_at} |",
        f"| Stages | {summary.done_count}/{summary.stage_count} |",
        f"| Cost | ${summary.total_cost:.2f} |",
        "",
    ]
    return "\n".join(lines)
