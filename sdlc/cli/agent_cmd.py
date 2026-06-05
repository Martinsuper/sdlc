import click


@click.command()
@click.option("--list", "list_agents", is_flag=True)
@click.option("--run", help="Run specific agent")
def agent(list_agents, run):
    click.echo("TODO: implement agent")
