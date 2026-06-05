import click


@click.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell):
    """Generate shell completion script."""
    prog_name = "sdlc"

    if shell == "bash":
        click.echo(
            f"# Add to ~/.bashrc:\n"
            f'eval "$(_{prog_name}_COMPLETION=bash source {prog_name})"'
        )
    elif shell == "zsh":
        click.echo(
            f"# Add to ~/.zshrc:\n"
            f'eval "$(_{prog_name}_COMPLETION=zsh source {prog_name})"'
        )
    elif shell == "fish":
        click.echo(
            f"# Add to ~/.config/fish/completions/{prog_name}.fish"
        )
