import click


@click.command()
@click.option("--since", default="7d", help="Lookback period")
@click.option("--by-model", is_flag=True)
@click.option("--by-stage", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def stats(since, by_model, by_stage, as_json):
    """Show pipeline statistics."""
    from sdlc.utils.paths import sdlc_home

    home = sdlc_home()
    db_path = home / "state.db"
    if not db_path.exists():
        click.echo("No data available. Run some pipelines first.")
        return

    from sdlc.state.store import StateStore

    store = StateStore(db_path)

    pipelines = store.list_pipelines()
    if not pipelines:
        click.echo("No pipelines found.")
        return

    total = len(pipelines)
    completed = sum(1 for p in pipelines if p.status.upper() == "COMPLETED")
    failed = sum(1 for p in pipelines if p.status.upper() == "FAILED")
    total_cost = sum(p.total_cost for p in pipelines)

    # Query cost-by-model from llm_calls table
    cost_by_model: dict[str, float] = {}
    try:
        rows = store.db.execute(
            "SELECT model, SUM(cost_usd) as cost FROM llm_calls GROUP BY model"
        ).fetchall()
        cost_by_model = {row["model"]: round(float(row["cost"]), 4) for row in rows}
    except Exception:
        cost_by_model = {}

    result = {
        "since": since,
        "total": total,
        "completed": completed,
        "failed": failed,
        "success_rate": round(completed / total * 100, 1) if total > 0 else 0,
        "total_cost": round(total_cost, 2),
        "cost_by_model": cost_by_model,
    }

    if as_json:
        import json

        click.echo(json.dinternal-monitorings(result, indent=2))
        return

    click.echo(f"Pipeline Statistics (since {since})")
    click.echo(f"  Total:        {total}")
    click.echo(f"  Completed:    {completed}")
    click.echo(f"  Failed:       {failed}")
    if total > 0:
        click.echo(f"  Success Rate: {completed / total * 100:.1f}%")
    else:
        click.echo("  Success Rate: N/A")
    click.echo(f"  Total Cost:   ${total_cost:.2f}")

    if by_model and cost_by_model:
        click.echo("\n  Cost by model:")
        for model_name, model_cost in cost_by_model.items():
            click.echo(f"    {model_name}: ${model_cost:.4f}")
    elif by_model:
        click.echo("\n  Cost by model: no data")
    if by_stage:
        click.echo("\n  Duration by stage (M2)")
