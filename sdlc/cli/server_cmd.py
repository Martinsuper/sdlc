"""`sdlc server` — run the optional self-hosted collaboration server (M-B2)."""

from __future__ import annotations

import click


@click.group()
def server() -> None:
    """Optional self-hosted server for team collaboration (shared state, approvals)."""


@server.command("start")
@click.option("--host", default="127.0.0.1", help="Bind host.")
@click.option("--port", default=8787, type=int, help="Bind port.")
def server_start(host: str, port: int) -> None:
    """Start the server (Ctrl-C to stop). Serves shared state + the read-only console."""
    from http.server import HTTPServer

    from sdlc.server.app import build_http_handler
    from sdlc.state.store import StateStore
    from sdlc.utils.paths import sdlc_home

    store = StateStore(sdlc_home() / "state.db")
    handler = build_http_handler(store)
    httpd = HTTPServer((host, port), handler)
    click.echo(f"sdlc server on http://{host}:{port}  (console at /console)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nstopping…")
        httpd.shutdown()


@server.command("status")
@click.option("--url", default=None, help="Server URL (defaults to configured).")
def server_status(url: str | None) -> None:
    """Check whether a server is reachable."""
    import httpx

    from sdlc.utils.config_loader import load_config

    if url is None:
        cfg = load_config()
        url = getattr(getattr(cfg, "server", None), "url", None)
    if not url:
        click.echo("No server URL configured.")
        return
    try:
        resp = httpx.get(f"{url.rstrip('/')}/pipelines", timeout=5.0)
        click.echo(f"reachable: {resp.status_code}")
    except Exception as e:
        click.echo(f"unreachable: {e}", err=True)
        raise SystemExit(1) from None
