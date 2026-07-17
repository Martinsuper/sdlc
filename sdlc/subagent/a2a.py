"""Agent-to-Agent (A2A) protocol prototype (M-C6).

M-A5 does in-process orchestration; this standardizes the interaction contract
so an sdlc agent can hand a task to an *external* agent system (e.g. a team's
own security-audit agent) and consume its result.

Design constraints:
  - align with community shapes (task / result / success-criteria envelopes),
    don't invent an island;
  - reuse the M-A5 task/result vocabulary;
  - optional advanced capability — never required for single-machine core;
  - external agents are gated by a whitelist, negotiate capabilities before
    dispatch, and every exchange is auditable.

The wire format is JSON envelopes; transport is HTTP via httpx. A missing/
unreachable peer degrades to an error result rather than raising into the
pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

A2A_PROTOCOL_VERSION = "0.1"


@dataclass
class A2ATask:
    """A task offered to an external agent (mirrors the M-A5 WorkerSpec)."""

    task_id: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    protocol_version: str = A2A_PROTOCOL_VERSION

    def to_envelope(self) -> dict[str, Any]:
        return {"kind": "a2a.task", **asdict(self)}


@dataclass
class A2AResult:
    """An external agent's response for a task."""

    task_id: str
    success: bool
    output: str = ""
    met_criteria: list[str] = field(default_factory=list)
    error: str | None = None
    protocol_version: str = A2A_PROTOCOL_VERSION

    def to_envelope(self) -> dict[str, Any]:
        return {"kind": "a2a.result", **asdict(self)}

    @classmethod
    def from_envelope(cls, data: dict[str, Any]) -> A2AResult:
        return cls(
            task_id=str(data.get("task_id", "")),
            success=bool(data.get("success", False)),
            output=str(data.get("output", "")),
            met_criteria=[str(c) for c in data.get("met_criteria", []) or []],
            error=data.get("error"),
            protocol_version=str(data.get("protocol_version", A2A_PROTOCOL_VERSION)),
        )


@dataclass
class Capabilities:
    """What an external agent advertises it can do (negotiation step)."""

    agent_id: str
    skills: list[str] = field(default_factory=list)
    protocol_version: str = A2A_PROTOCOL_VERSION

    def supports(self, skill: str) -> bool:
        return skill in self.skills

    def compatible(self) -> bool:
        """Same major protocol version => compatible (semver-ish, prototype)."""
        return self.protocol_version.split(".")[0] == A2A_PROTOCOL_VERSION.split(".")[0]

    @classmethod
    def from_envelope(cls, data: dict[str, Any]) -> Capabilities:
        return cls(
            agent_id=str(data.get("agent_id", "")),
            skills=[str(s) for s in data.get("skills", []) or []],
            protocol_version=str(data.get("protocol_version", A2A_PROTOCOL_VERSION)),
        )


class A2AClient:
    """Dispatch tasks to whitelisted external agents over HTTP.

    An external endpoint must be in ``allowed_endpoints`` (whitelist) before any
    request is made. Capabilities are fetched and checked for compatibility
    before a task is dispatched.
    """

    def __init__(self, allowed_endpoints: set[str] | None = None, timeout: float = 30.0) -> None:
        self.allowed_endpoints = allowed_endpoints or set()
        self.timeout = timeout

    def is_allowed(self, endpoint: str) -> bool:
        return endpoint in self.allowed_endpoints

    async def negotiate(self, endpoint: str) -> Capabilities | None:
        """GET the peer's capabilities. Returns None if not allowed/unreachable/
        incompatible."""
        if not self.is_allowed(endpoint):
            return None
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{endpoint.rstrip('/')}/a2a/capabilities")
                resp.raise_for_status()
                caps = Capabilities.from_envelope(resp.json())
        except Exception:
            return None
        return caps if caps.compatible() else None

    async def dispatch(self, endpoint: str, task: A2ATask) -> A2AResult:
        """Send a task to an external agent; return its result.

        Refuses non-whitelisted endpoints and returns an error result (never
        raises) so a flaky peer cannot break the calling pipeline."""
        if not self.is_allowed(endpoint):
            return A2AResult(
                task_id=task.task_id, success=False, error=f"endpoint not whitelisted: {endpoint}"
            )
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{endpoint.rstrip('/')}/a2a/task", json=task.to_envelope()
                )
                resp.raise_for_status()
                return A2AResult.from_envelope(resp.json())
        except Exception as e:
            return A2AResult(task_id=task.task_id, success=False, error=str(e))
