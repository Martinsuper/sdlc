import click


@click.group()
def rule():
    """Manage rules."""


@rule.command("list")
@click.option("--level", type=click.Choice(["MUST", "SHOULD", "MAY"]))
@click.option("--category", help="Filter by category")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def rule_list(level, category, fmt):
    click.echo(f"TODO: implement rule list | level={level}")


@rule.command("show")
@click.argument("rule_id")
def rule_show(rule_id):
    click.echo(f"TODO: implement rule show | rule_id={rule_id}")


@rule.command("add")
@click.option("--from-file", type=click.Path(exists=True), help="Batch add from YAML file")
@click.option("-", "use_stdin", is_flag=True)
def rule_add(from_file, use_stdin):
    click.echo("TODO: implement rule add")


@rule.command("disable")
@click.argument("rule_id")
@click.option("--until", help="Re-enable date (ISO)")
@click.option("--reason", help="Reason for disabling")
def rule_disable(rule_id, until, reason):
    click.echo(f"TODO: implement rule disable | rule_id={rule_id}")


@rule.command("check")
@click.argument("stage_id")
def rule_check(stage_id):
    click.echo(f"TODO: implement rule check | stage_id={stage_id}")


@rule.command("violations")
@click.option("--since", default="7d", help="Lookback period")
def rule_violations(since):
    click.echo("TODO: implement rule violations")
