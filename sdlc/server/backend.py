"""Remote state backend with local fallback (M-B2).

When a server URL is configured, CLI state reads/writes go over HTTP; when the
server is unreachable, calls transparently fall back to the local StateStore so
"CLI works standalone" always holds. This is the seam that lets a team share
state without the CLI ever hard-depending on the server.
"""

from __future__ import annotations

from typing import Any, Protocol

from sdlc.state.store import StateStore


class StateBackend(Protocol):
    def list_pipelines(self, **kw: Any) -> list[Any]: ...
    def load_waiting(self, pipeline_id: str, **kw: Any) -> list[dict[str, Any]]: ...
    def resolve_waiting(
        self, pipeline_id: str, kind: str, ref_id: str, answer: dict[str, Any]
    ) -> bool: ...


class RemoteStateBackend:
    """Talks to the server over HTTP, falling back to a local StateStore on any
    connection/timeout error so the CLI never blocks on a down server."""

    def __init__(self, base_url: str, token: str, local_fallback: StateStore, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.local = local_fallback
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def list_pipelines(self, **kw: Any) -> list[Any]:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout) as c:
                resp = c.get(f"{self.base_url}/pipelines", params=kw, headers=self._headers())
                resp.raise_for_status()
                return list(resp.json().get("pipelines", []))
        except Exception:
            return self.local.list_pipelines(**kw)

    def load_waiting(self, pipeline_id: str, **kw: Any) -> list[dict[str, Any]]:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout) as c:
                resp = c.get(
                    f"{self.base_url}/waiting",
                    params={"pipeline_id": pipeline_id, **kw},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return list(resp.json().get("waiting", []))
        except Exception:
            return self.local.load_waiting(pipeline_id, **kw)

    def resolve_waiting(
        self, pipeline_id: str, kind: str, ref_id: str, answer: dict[str, Any]
    ) -> bool:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout) as c:
                resp = c.post(
                    f"{self.base_url}/approve",
                    json={"pipeline_id": pipeline_id, "gate_id": ref_id, **answer},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return bool(resp.json().get("ok", False))
        except Exception:
            return self.local.resolve_waiting(pipeline_id, kind, ref_id, answer)
