import click


@click.group()
def config():
    """Manage configuration."""


@config.command("show")
@click.option("--json", "as_json", is_flag=True)
def config_show(as_json):
    click.echo("TODO: implement config show")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    click.echo(f"TODO: implement config set | {key}={value}")


@config.command("test-llm")
def config_test_llm():
    click.echo("TODO: implement config test-llm")
