"""rule_cmd — Rule management CLI commands."""

import click

from sdlc.rule.engine import RuleEngine, RuleNotFoundError
from sdlc.rule.models import RuleLevel
from sdlc.utils.paths import project_root


def _load_engine() -> RuleEngine:
    """Create a RuleEngine and load rules from the project KB if available."""
    engine = RuleEngine()
    rules_dir = project_root() / "doc" / "kb" / "rules"
    if rules_dir.exists():
        for f in rules_dir.glob("*.yaml"):
            engine.load_from_yaml(f)
    return engine


@click.group()
def rule():
    """Manage rules."""


@rule.command("list")
@click.option("--level", type=click.Choice(["MUST", "SHOULD", "MAY"]))
@click.option("--category", help="Filter by category")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def rule_list(level, category, fmt):
    """List all rules."""
    engine = _load_engine()
    rules = engine.list_rules(category=category, level=RuleLevel(level) if level else None)
    if not rules:
        click.echo("No rules found")
        return
    if fmt == "json":
        import json

        click.echo(json.dinternal-monitorings([r.model_dinternal-monitoring() for r in rules], indent=2, default=str))
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Rules")
    table.add_column("ID", style="cyan")
    table.add_column("Level", style="red")
    table.add_column("Category", style="green")
    table.add_column("Action", style="yellow")
    table.add_column("Enforcer")
    for r in rules:
        level_style = (
            "bold red"
            if r.level in ("MUST", "MUST_NOT")
            else "yellow" if r.level in ("SHOULD", "SHOULD_NOT") else "dim"
        )
        table.add_row(
            r.id,
            f"[{level_style}]{r.level}[/{level_style}]",
            r.category,
            r.action,
            r.enforcer,
        )
    console.print(table)


@rule.command("show")
@click.argument("rule_id")
def rule_show(rule_id):
    """Show rule details."""
    engine = _load_engine()
    try:
        r = engine.get(rule_id)
        click.echo(f"ID:          {r.id}")
        click.echo(f"Level:       {r.level}")
        click.echo(f"Category:    {r.category}")
        click.echo(f"Action:      {r.action}")
        click.echo(f"Enforcer:    {r.enforcer}")
        click.echo(f"Severity:    {r.severity}")
        click.echo(f"Description: {r.description}")
        if r.pattern:
            click.echo(f"Pattern:     {r.pattern}")
        if r.applies_to:
            click.echo(f"Applies To:  {', '.join(r.applies_to)}")
        if r.scope:
            click.echo(f"Scope:       {r.scope}")
        if r.references:
            click.echo(f"References:  {', '.join(r.references)}")
        if r.disabled:
            click.echo(f"Disabled:    Yes (reason: {r.disabled_reason}, until: {r.disabled_until})")
    except RuleNotFoundError:
        click.echo(f"Rule not found: {rule_id}", err=True)
        raise SystemExit(1) from None


@rule.command("add")
@click.option("--from-file", type=click.Path(exists=True), help="Batch add from YAML file")
def rule_add(from_file):
    """Add rules from YAML file."""
    if from_file:
        from pathlib import Path

        from sdlc.rule.loader import load_rules_from_yaml

        rules = load_rules_from_yaml(Path(from_file))
        click.echo(f"Loaded {len(rules)} rules from {from_file}")
        click.echo("Note: Rules are loaded in memory only. To persist, add the YAML file to doc/kb/rules/")
    else:
        click.echo("Please specify --from-file")


@rule.command("disable")
@click.argument("rule_id")
@click.option("--until", help="Re-enable date (ISO format)")
@click.option("--reason", help="Reason for disabling")
def rule_disable(rule_id, until, reason):
    """Temporarily disable a rule."""
    engine = _load_engine()
    try:
        engine.disable(rule_id, until=until or "2099-12-31", reason=reason or "Manually disabled")
        click.echo(f"Rule '{rule_id}' disabled until {until or 'indefinitely'}")
    except RuleNotFoundError:
        click.echo(f"Rule not found: {rule_id}", err=True)
        raise SystemExit(1) from None


@rule.command("check")
@click.argument("stage_id")
def rule_check(stage_id):
    """Check rules for a stage."""
    engine = _load_engine()
    rules = engine.for_stage(stage_id)
    click.echo(f"Rules for stage '{stage_id}': {len(rules)}")
    for r in rules:
        click.echo(f"  [{r.level}] {r.id}: {r.description or r.message or 'No description'}")


@rule.command("violations")
@click.option("--since", default="7d", help="Lookback period")
def rule_violations(since):
    """Show rule violations history."""
    click.echo(f"Rule violations history (since {since}) — requires audit log (M2)")
