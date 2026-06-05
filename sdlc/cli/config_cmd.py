"""config_cmd — Configuration management CLI commands."""

import contextlib
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
    """Set a configuration value and persist it."""
    from sdlc.utils.paths import sdlc_home
    from sdlc.utils.yaml_io import load_yaml, save_yaml

    home = sdlc_home()
    home.mkdir(exist_ok=True)
    config_path = home / "config.yaml"

    # Load existing config
    if config_path.exists():
        cfg = load_yaml(config_path) or {}
        if not isinstance(cfg, dict):
            cfg = {}
    else:
        cfg = {}

    # Set nested key (e.g., "llm.primary_model")
    keys = key.split(".")
    current = cfg
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]

    # Try to parse value as int/float/bool
    parsed_value: object = value
    if value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"
    else:
        with contextlib.suppress(ValueError):
            parsed_value = int(value)
        if isinstance(parsed_value, str):
            with contextlib.suppress(ValueError):
                parsed_value = float(value)

    current[keys[-1]] = parsed_value

    # Save
    save_yaml(config_path, cfg)
    click.echo(f"Set {key} = {parsed_value}")
    click.echo(f"Saved to {config_path}")


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


@config.command("reset")
@click.option("--confirm", is_flag=True, help="Confirm reset")
def config_reset(confirm):
    """Reset configuration to defaults."""
    if not confirm:
        click.echo("This will delete your user configuration. Use --confirm to proceed.")
        return
    from sdlc.utils.paths import sdlc_home

    config_path = sdlc_home() / "config.yaml"
    if config_path.exists():
        config_path.unlink()
        click.echo("Configuration reset to defaults")
    else:
        click.echo("No user configuration found")
