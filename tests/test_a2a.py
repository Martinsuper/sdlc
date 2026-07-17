"""Tests for M-C6 A2A protocol prototype (envelopes + whitelisted client)."""

from __future__ import annotations

import httpx
import pytest
import respx

from sdlc.subagent.a2a import (
    A2A_PROTOCOL_VERSION,
    A2AClient,
    A2AResult,
    A2ATask,
    Capabilities,
)

# --------------------------------------------------------------------------- #
# Envelopes
# --------------------------------------------------------------------------- #

def test_task_envelope_roundtrip_shape():
    task = A2ATask(task_id="t1", description="audit auth", acceptance_criteria=["no plaintext"])
    env = task.to_envelope()
    assert env["kind"] == "a2a.task"
    assert env["task_id"] == "t1"
    assert env["protocol_version"] == A2A_PROTOCOL_VERSION


def test_result_from_envelope():
    r = A2AResult.from_envelope(
        {"task_id": "t1", "success": True, "output": "ok", "met_criteria": ["c1"]}
    )
    assert r.success and r.output == "ok" and r.met_criteria == ["c1"]


def test_capabilities_compatible_by_major_version():
    same = Capabilities(agent_id="x", skills=["audit"], protocol_version="0.9")
    assert same.compatible()  # same major (0)
    diff = Capabilities(agent_id="x", protocol_version="1.0")
    assert not diff.compatible()


def test_capabilities_supports():
    caps = Capabilities(agent_id="x", skills=["audit", "review"])
    assert caps.supports("audit")
    assert not caps.supports("deploy")


# --------------------------------------------------------------------------- #
# Whitelist
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_dispatch_refuses_non_whitelisted():
    client = A2AClient(allowed_endpoints=set())
    result = await client.dispatch("http://evil.example", A2ATask(task_id="t1", description="x"))
    assert not result.success
    assert "not whitelisted" in (result.error or "")


@pytest.mark.asyncio
async def test_negotiate_refuses_non_whitelisted():
    client = A2AClient(allowed_endpoints=set())
    assert await client.negotiate("http://evil.example") is None


# --------------------------------------------------------------------------- #
# HTTP dispatch (mocked)
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
@respx.mock
async def test_dispatch_success():
    endpoint = "http://peer.local"
    respx.post(f"{endpoint}/a2a/task").mock(
        return_value=httpx.Response(200, json={"task_id": "t1", "success": True, "output": "done"})
    )
    client = A2AClient(allowed_endpoints={endpoint})
    result = await client.dispatch(endpoint, A2ATask(task_id="t1", description="audit"))
    assert result.success and result.output == "done"


@pytest.mark.asyncio
@respx.mock
async def test_dispatch_peer_error_degrades():
    endpoint = "http://peer.local"
    respx.post(f"{endpoint}/a2a/task").mock(return_value=httpx.Response(500))
    client = A2AClient(allowed_endpoints={endpoint})
    result = await client.dispatch(endpoint, A2ATask(task_id="t1", description="x"))
    # A failing peer yields an error result, never raises into the pipeline.
    assert not result.success
    assert result.error


@pytest.mark.asyncio
@respx.mock
async def test_negotiate_incompatible_version_rejected():
    endpoint = "http://peer.local"
    respx.get(f"{endpoint}/a2a/capabilities").mock(
        return_value=httpx.Response(
            200, json={"agent_id": "peer", "skills": ["audit"], "protocol_version": "9.0"}
        )
    )
    client = A2AClient(allowed_endpoints={endpoint})
    assert await client.negotiate(endpoint) is None  # major version mismatch


@pytest.mark.asyncio
@respx.mock
async def test_negotiate_success():
    endpoint = "http://peer.local"
    respx.get(f"{endpoint}/a2a/capabilities").mock(
        return_value=httpx.Response(
            200, json={"agent_id": "peer", "skills": ["audit"], "protocol_version": "0.1"}
        )
    )
    client = A2AClient(allowed_endpoints={endpoint})
    caps = await client.negotiate(endpoint)
    assert caps is not None and caps.supports("audit")
