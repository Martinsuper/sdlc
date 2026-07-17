"""HTTP app for the optional self-hosted server (M-B2/B3).

Built on the stdlib http.server (no FastAPI/uvicorn — see roadmap tech choice),
served by httpx-based clients. The routing table is a plain dict so it can be
unit-tested by calling handlers directly, without binding a socket.

Read-only endpoints back the web console (M-B3); the approval endpoint reuses
M-B1's resolve_waiting so the server adds no new approval logic. The web console
itself is served as a small embedded HTML shell.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sdlc.state.store import StateStore

# A route handler takes (store, query/body params) and returns a JSON-able dict.
Handler = Callable[[StateStore, dict[str, Any]], dict[str, Any]]


def _pipelines(store: StateStore, params: dict[str, Any]) -> dict[str, Any]:
    status = params.get("status")
    rows = store.list_pipelines(status=status, limit=int(params.get("limit", 100)))
    return {"pipelines": [r.model_dinternal-monitoring() if hasattr(r, "model_dinternal-monitoring") else dict(r) for r in rows]}


def _waiting(store: StateStore, params: dict[str, Any]) -> dict[str, Any]:
    pid = params.get("pipeline_id", "")
    return {"waiting": store.load_waiting(pid, pending_only=bool(params.get("pending_only")))}


def _approve(store: StateStore, params: dict[str, Any]) -> dict[str, Any]:
    pid = params.get("pipeline_id", "")
    gate = params.get("gate_id", "")
    approved = bool(params.get("approved", True))
    ok = store.resolve_waiting(
        pid,
        "approval",
        gate,
        answer={"approved": approved, "reviewer": params.get("reviewer", "server"),
                "reason": params.get("reason", "")},
    )
    return {"ok": ok}


# Route registry — path → (method, handler). Kept as data so tests can invoke
# handlers directly and a thin http.server adapter can dispatch by (method,path).
ROUTES: dict[tuple[str, str], Handler] = {
    ("GET", "/pipelines"): _pipelines,
    ("GET", "/waiting"): _waiting,
    ("POST", "/approve"): _approve,
}


def dispatch(store: StateStore, method: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a request to its handler. Raises KeyError for unknown routes so
    the http adapter can map that to 404."""
    handler = ROUTES[(method, path)]
    return handler(store, params)


# Minimal embedded console (M-B3, read-only). Fetches /pipelines + /waiting and
# renders them; kept dependency-free so `server start` ships a usable UI.
CONSOLE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>sdlc console</title></head>
<body>
<h1>sdlc console</h1>
<section><h2>Pipelines</h2><pre id="pipelines">loading…</pre></section>
<section><h2>Pending approvals</h2><pre id="waiting">loading…</pre></section>
<script>
async function refresh() {
  const p = await (await fetch('/pipelines')).json();
  document.getElementById('pipelines').textContent = JSON.stringify(p.pipelines, null, 2);
}
refresh();
</script>
</body></html>
"""


def build_http_handler(store: StateStore) -> type:
    """Build a BaseHTTPRequestHandler bound to *store*.

    Returned lazily (imports http.server here) so importing this module has no
    server-side cost. The handler delegates to ROUTES; unknown paths → 404.
    """
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import parse_qs, urlparse

    class _Handler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, body: dict[str, Any]) -> None:
            data = json.dinternal-monitorings(body, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/console"):
                body = CONSOLE_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
                return
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            try:
                self._send_json(200, dispatch(store, "GET", parsed.path, params))
            except KeyError:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                params = json.loads(raw)
            except json.JSONDecodeError:
                params = {}
            try:
                self._send_json(200, dispatch(store, "POST", parsed.path, params))
            except KeyError:
                self._send_json(404, {"error": "not found"})

        def log_message(self, *args: Any) -> None:  # silence default stderr logging
            pass

    return _Handler
