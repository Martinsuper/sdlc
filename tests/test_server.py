"""Tests for M-B2/B3/B4 server, remote backend, and IM notifiers.

NOTE on scope: these cover the *pure/unit-testable* surface — route dispatch
(without binding a socket), remote→local fallback, and card construction.
Full runtime verification (actually serving HTTP, real Feishu/Slack delivery,
button callbacks) requires a live environment and is out of scope for pytest.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from sdlc.integrations.notify import FeishuNotifier, SlackNotifier, get_notifier
from sdlc.server.app import dispatch
from sdlc.server.backend import RemoteStateBackend
from sdlc.state.store import StateStore


def _store(tmp_path) -> StateStore:
    s = StateStore(tmp_path / "s.db")
    s.save_pipeline(pipeline_id="p1", entry_kind="feature", profile_id="new-feature", status="RUNNING")
    return s


# --------------------------------------------------------------------------- #
# Server route dispatch (in-process, no socket)
# --------------------------------------------------------------------------- #

def test_dispatch_pipelines(tmp_path):
    store = _store(tmp_path)
    out = dispatch(store, "GET", "/pipelines", {})
    assert "pipelines" in out
    assert any(p["id"] == "p1" for p in out["pipelines"])


def test_dispatch_waiting_and_approve(tmp_path):
    store = _store(tmp_path)
    store.save_waiting("p1", "approval", "g1", {"reason": "review"}, stage_id="s1")
    waiting = dispatch(store, "GET", "/waiting", {"pipeline_id": "p1", "pending_only": True})
    assert len(waiting["waiting"]) == 1

    res = dispatch(store, "POST", "/approve", {"pipeline_id": "p1", "gate_id": "g1", "approved": True})
    assert res["ok"] is True
    assert not store.has_pending_waiting("p1")


def test_dispatch_unknown_route_raises(tmp_path):
    with pytest.raises(KeyError):
        dispatch(_store(tmp_path), "GET", "/nope", {})


# --------------------------------------------------------------------------- #
# RemoteStateBackend fallback (M-B2 core guarantee)
# --------------------------------------------------------------------------- #

@respx.mock
def test_remote_backend_uses_server_when_up(tmp_path):
    respx.get("http://srv/pipelines").mock(
        return_value=httpx.Response(200, json={"pipelines": [{"id": "remote-1"}]})
    )
    be = RemoteStateBackend("http://srv", token="t", local_fallback=_store(tmp_path))
    rows = be.list_pipelines()
    assert rows == [{"id": "remote-1"}]


@respx.mock
def test_remote_backend_falls_back_when_down(tmp_path):
    respx.get("http://srv/pipelines").mock(side_effect=httpx.ConnectError("down"))
    be = RemoteStateBackend("http://srv", token="t", local_fallback=_store(tmp_path))
    # Server unreachable => local store answers; the CLI is never blocked.
    rows = be.list_pipelines()
    assert any(getattr(r, "id", None) == "p1" for r in rows)


@respx.mock
def test_remote_backend_resolve_falls_back(tmp_path):
    store = _store(tmp_path)
    store.save_waiting("p1", "approval", "g1", {"reason": "x"})
    respx.post("http://srv/approve").mock(side_effect=httpx.ConnectError("down"))
    be = RemoteStateBackend("http://srv", token="t", local_fallback=store)
    ok = be.resolve_waiting("p1", "approval", "g1", {"approved": True})
    assert ok  # resolved locally despite server being down


# --------------------------------------------------------------------------- #
# IM notifier card construction (M-B4)
# --------------------------------------------------------------------------- #

def test_feishu_card_has_approve_reject_buttons():
    card = FeishuNotifier("http://hook").build_approval_card("p1", "g1", "needs review")
    actions = card["card"]["elements"][-1]["actions"]
    values = [a["value"]["action"] for a in actions]
    assert values == ["approve", "reject"]


def test_slack_card_has_buttons():
    card = SlackNotifier("http://hook").build_approval_card("p1", "g1", "needs review")
    action_ids = [e["action_id"] for e in card["blocks"][-1]["elements"]]
    assert action_ids == ["sdlc_approve", "sdlc_reject"]


def test_get_notifier_factory():
    assert get_notifier("feishu", "http://h").name == "feishu"
    assert get_notifier("slack", "http://h").name == "slack"
    with pytest.raises(ValueError, match="Unknown notification channel"):
        get_notifier("carrier-pigeon", "http://h")


@pytest.mark.asyncio
@respx.mock
async def test_notify_delivery_failsafe():
    respx.post("http://hook").mock(side_effect=httpx.ConnectError("down"))
    # Delivery failure returns False, never raises (pipeline is not blocked).
    ok = await FeishuNotifier("http://hook").notify_pending("p1", "g1", "x")
    assert ok is False
