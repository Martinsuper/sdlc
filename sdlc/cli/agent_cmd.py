import click


@click.group()
def agent():
    """Browse subagents."""


@agent.command("list")
def agent_list():
    """List all subagents."""
    from sdlc.subagent.builtin import register_builtins
    from sdlc.subagent.registry import SubagentRegistry

    registry = SubagentRegistry()
    register_builtins(registry)
    agents = registry.list()

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Subagents")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Role", style="green")
    table.add_column("Model", style="yellow")
    table.add_column("Max Iter", justify="right")

    for a in agents:
        table.add_row(a.id, a.name, a.role, a.model, str(a.max_iter))
    console.print(table)


@agent.command("show")
@click.argument("agent_id")
def agent_show(agent_id):
    """Show subagent details."""
    from sdlc.subagent.builtin import register_builtins
    from sdlc.subagent.registry import SubagentNotFoundError, SubagentRegistry

    registry = SubagentRegistry()
    register_builtins(registry)
    try:
        a = registry.get(agent_id)
    except SubagentNotFoundError:
        click.echo(f"Subagent not found: {agent_id}", err=True)
        raise SystemExit(1) from None

    click.echo(f"ID:          {a.id}")
    click.echo(f"Name:        {a.name}")
    click.echo(f"Role:        {a.role}")
    click.echo(f"Model:       {a.model}")
    click.echo(f"Max Iter:    {a.max_iter}")
    click.echo(f"Tools:       {', '.join(a.tools) if a.tools else 'None'}")
    click.echo(f"KB Inject:   {', '.join(a.kb_inject) if a.kb_inject else 'None'}")
