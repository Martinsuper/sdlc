"""llm_cmd -- LLM provider management CLI commands."""

import click


@click.group()
def llm():
    """Manage LLM providers."""


@llm.command("list")
def llm_list():
    """List configured and preset LLM providers."""
    from sdlc.llm.presets import list_presets
    from sdlc.utils.config_loader import load_config

    cfg = load_config()

    click.echo("=== Current Configuration ===")
    click.echo(f"  Provider:    {cfg.llm.provider}")
    click.echo(f"  Model:       {cfg.llm.model}")
    click.echo(f"  Base URL:    {cfg.llm.base_url or '(default)'}")
    click.echo(f"  API Key Env: {cfg.llm.api_key_env}")
    if cfg.llm.fallback_provider:
        click.echo(f"  Fallback:    {cfg.llm.fallback_provider} / {cfg.llm.fallback_model}")

    click.echo("\n=== Available Presets ===")
    for p in list_presets():
        click.echo(f"  {p.id:15s}  {p.name}")
        click.echo(f"  {'':15s}  {p.description}")
        click.echo(f"  {'':15s}  model={p.default_model}  url={p.base_url}")
        click.echo()


@llm.command("test")
def llm_test():
    """Test LLM provider connectivity."""
    import os

    from sdlc.llm.presets import list_presets
    from sdlc.utils.config_loader import load_config

    cfg = load_config()

    click.echo("Testing LLM providers...\n")

    # Test current provider
    click.echo(f"[1] Current: {cfg.llm.provider} ({cfg.llm.model})")
    api_key = os.environ.get(cfg.llm.api_key_env, "")
    if api_key:
        try:
            from sdlc.llm.provider_factory import ProviderFactory

            provider = ProviderFactory.create(cfg.llm)
            info = provider.model_info(cfg.llm.model)
            click.echo(f"    OK: Provider initialized: {info.name} (context={info.max_context})")
        except Exception as e:
            click.echo(f"    FAIL: {e}")
    else:
        click.echo(f"    SKIP: API key not set ({cfg.llm.api_key_env})")

    # Test fallback if configured
    if cfg.llm.fallback_provider:
        click.echo(f"\n[2] Fallback: {cfg.llm.fallback_provider}")
        try:
            from sdlc.llm.provider_factory import ProviderFactory

            fb = ProviderFactory.create_fallback(cfg.llm)
            if fb:
                click.echo("    OK: Fallback provider initialized")
            else:
                click.echo("    FAIL: Could not create fallback provider")
        except Exception as e:
            click.echo(f"    FAIL: {e}")

    # Quick test of preset API key availability
    click.echo("\n=== Preset API Key Check ===")
    for p in list_presets():
        key = os.environ.get(p.api_key_env, "")
        status = "OK" if key else "not set"
        click.echo(f"  {p.id:15s}  {status}  ({p.api_key_env})")


@llm.command("presets")
def llm_presets():
    """List available LLM provider presets."""
    from sdlc.llm.presets import list_presets

    click.echo("Available LLM provider presets:\n")
    click.echo(f"{'ID':15s}  {'Name':25s}  {'Default Model':30s}  {'Base URL'}")
    click.echo("-" * 110)
    for p in list_presets():
        click.echo(f"{p.id:15s}  {p.name:25s}  {p.default_model:30s}  {p.base_url}")

    click.echo("\nUsage:")
    click.echo("  sdlc config set llm.provider deepseek")
    click.echo("  sdlc config set llm.api_key_env DEEPSEEK_API_KEY")
    click.echo("  export DEEPSEEK_API_KEY=sk-...")
    click.echo("  sdlc llm test")
