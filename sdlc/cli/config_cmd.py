"""config_cmd — Configuration management CLI commands."""

import os

import click


@click.group()
def config():
    """Manage configuration."""


@config.command("show")
@click.option("--json", "as_json", is_flag=True)
def config_show(as_json):
    """Show current configuration."""
    from sdlc.utils.config_loader import load_config

    cfg = load_config()
    if as_json:
        click.echo(cfg.model_dinternal-monitoring_json(indent=2))
    else:
        click.echo(f"LLM Provider:   {cfg.llm.provider}")
        click.echo(f"Primary Model:  {cfg.llm.model}")
        click.echo(f"Cache Enabled:  {cfg.cache_enabled}")
        click.echo(f"Log Level:      {cfg.log_level}")
        click.echo(f"Audit Enabled:  {cfg.audit_enabled}")


@config.command("get")
@click.argument("key")
def config_get(key):
    """Get a configuration value."""
    from sdlc.utils.config_loader import load_config

    cfg = load_config()
    data = cfg.model_dinternal-monitoring()
    keys = key.split(".")
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            click.echo(f"Key not found: {key}", err=True)
            raise SystemExit(1)
    click.echo(str(value))


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    click.echo(f"Setting {key}={value}")
    click.echo("Note: Configuration persistence will be available in M2.")


@config.command("path")
def config_path():
    """Show configuration file paths."""
    from sdlc.utils.paths import sdlc_home

    home = sdlc_home()
    click.echo(f"SDLC Home:      {home}")
    click.echo(f"User Config:    {home / 'config.yaml'}")
    click.echo("Project Config: .sdlc/ext/config.yaml")


@config.command("test-llm")
def config_test_llm():
    """Test LLM connectivity."""
    click.echo("Testing LLM connectivity...")
    try:
        from sdlc.llm.anthropic_provider import AnthropicProvider

        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if key:
            AnthropicProvider(api_key=key)
            click.echo("  Anthropic: Provider initialized successfully")
        else:
            click.echo("  Anthropic: Skipped (ANTHROPIC_API_KEY not set)")
    except Exception as e:
        click.echo(f"  Anthropic: Failed — {e}")
    try:
        from sdlc.llm.openai_provider import OpenAIProvider

        key = os.environ.get("OPENAI_API_KEY", "")
        if key:
            OpenAIProvider(api_key=key)
            click.echo("  OpenAI: Provider initialized successfully")
        else:
            click.echo("  OpenAI: Skipped (OPENAI_API_KEY not set)")
    except Exception as e:
        click.echo(f"  OpenAI: Failed — {e}")
    click.echo("Note: API key validation requires actual API calls (M2).")
