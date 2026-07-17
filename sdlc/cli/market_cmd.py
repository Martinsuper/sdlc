"""`sdlc market` — discover, install, and publish marketplace plugins (M-C2)."""

from __future__ import annotations

import pathlib

import click

_DEFAULT_REGISTRY = "https://raw.githubusercontent.com/your-org/sdlc-registry/main/index.json"


def _registry_source(override: str | None) -> str:
    if override:
        return override
    # Private/enterprise registries: config wins over the public default.
    try:
        from sdlc.utils.config_loader import load_config

        cfg = load_config()
        url = getattr(getattr(cfg, "market", None), "url", None)
        if url:
            return str(url)
    except Exception:
        pass
    return _DEFAULT_REGISTRY


@click.group()
def market() -> None:
    """Discover, install, and publish sdlc extension plugins."""


@market.command("search")
@click.argument("keyword", default="")
@click.option("--type", "type_filter", default=None, help="Filter by plugin type.")
@click.option("--registry", default=None, help="Registry URL/path override.")
def market_search(keyword: str, type_filter: str | None, registry: str | None) -> None:
    """Search the registry for plugins."""
    from sdlc.market.registry_client import RegistryClient

    try:
        results = RegistryClient(_registry_source(registry)).search(keyword, type_filter)
    except Exception as e:
        click.echo(f"Could not reach registry: {e}", err=True)
        raise SystemExit(1) from None
    if not results:
        click.echo("No matching plugins.")
        return
    for entry in results:
        badge = "✓" if entry.verified else " "
        click.echo(
            f"  [{badge}] {entry.id:28s} {entry.type:10s} v{entry.version}  "
            f"↓{entry.downloads}  ★{entry.rating}"
        )


@market.command("install")
@click.argument("plugin_id")
@click.option("--registry", default=None, help="Registry URL/path override.")
@click.option("--from-file", "from_file", default=None, help="Install a local .sdlcpkg instead.")
def market_install(plugin_id: str, registry: str | None, from_file: str | None) -> None:
    """Install a plugin into the user extension dir."""
    from sdlc.market.installer import install_package
    from sdlc.market.registry_client import RegistryClient
    from sdlc.market.trust import TrustError

    if from_file:
        try:
            dest = install_package(pathlib.Path(from_file))
        except (TrustError, ValueError) as e:
            click.echo(f"Install failed: {e}", err=True)
            raise SystemExit(1) from None
        click.echo(f"Installed {plugin_id} to {dest}")
        return

    entry = RegistryClient(_registry_source(registry)).find(plugin_id)
    if entry is None:
        click.echo(f"Plugin not found in registry: {plugin_id}", err=True)
        raise SystemExit(1)
    click.echo(
        f"Would download {entry.id} v{entry.version} from {entry.download_url}\n"
        f"(network download not performed here; use --from-file for a local package)."
    )


@market.command("publish")
@click.argument("pkg_path")
def market_publish(pkg_path: str) -> None:
    """Validate a package and print the registry entry to submit."""
    import json

    from sdlc.plugin.packer import read_manifest_from_pkg

    try:
        manifest = read_manifest_from_pkg(pathlib.Path(pkg_path))
    except Exception as e:
        click.echo(f"Cannot read package: {e}", err=True)
        raise SystemExit(1) from None
    entry = {
        "id": manifest.id,
        "type": manifest.type,
        "version": manifest.version,
        "sdlc_version": manifest.sdlc_version,
        "author": manifest.author,
        "checksum": manifest.checksum,
        "verified": False,
    }
    click.echo("Submit this entry to the registry index.json:")
    click.echo(json.dinternal-monitorings(entry, ensure_ascii=False, indent=2))
