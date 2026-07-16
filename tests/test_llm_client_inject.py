"""Tests for MultiLLMClient config injection (temperature/max_tokens) and
fallback-on-LLMError behavior.

Regression coverage for the bug where configured llm.temperature never reached
requests (subagent pool built CompletionRequest without temperature, so the
model default 0.7 was always sent — rejected by thinking/adaptive gateways).
"""

from __future__ import annotations

import pytest

from sdlc.llm.anthropic_provider import LLMRateLimitError
from sdlc.llm.client import MultiLLMClient
from sdlc.llm.models import CompletionRequest, CompletionResponse, Message, Role
from sdlc.utils.exceptions import LLMError


class _RecordingProvider:
    """Captures the last request it received; returns a trivial response."""

    def __init__(self, name: str = "primary", raises: Exception | None = None) -> None:
        self.name = name
        self.raises = raises
        self.last_req: CompletionRequest | None = None
        self.calls = 0

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        self.last_req = req
        if self.raises is not None:
            raise self.raises
        return CompletionResponse(id=self.name, model=req.model, content=[])


class _NoRouter:
    """Router that never rewrites the model (isolates temperature logic)."""

    def route(self, req: CompletionRequest) -> str | None:
        return None


def _req(**kw) -> CompletionRequest:
    return CompletionRequest(messages=[Message(role=Role.USER, content="hi")], **kw)


@pytest.mark.asyncio
async def test_configured_temperature_injected_when_request_unset():
    primary = _RecordingProvider()
    client = MultiLLMClient(primary=primary, router=_NoRouter(), temperature=0.3, max_tokens=4096)
    await client.complete(_req())
    assert primary.last_req.temperature == 0.3
    assert primary.last_req.max_tokens == 4096


@pytest.mark.asyncio
async def test_request_temperature_not_overridden():
    primary = _RecordingProvider()
    client = MultiLLMClient(primary=primary, router=_NoRouter(), temperature=0.3)
    await client.complete(_req(temperature=1.0))
    assert primary.last_req.temperature == 1.0


@pytest.mark.asyncio
async def test_none_config_temperature_stays_unset_for_omission():
    # temperature=None config => request stays None => provider omits it entirely
    primary = _RecordingProvider()
    client = MultiLLMClient(primary=primary, router=_NoRouter(), temperature=None)
    await client.complete(_req())
    assert primary.last_req.temperature is None


@pytest.mark.asyncio
async def test_max_tokens_falls_back_to_hard_default_when_all_unset():
    primary = _RecordingProvider()
    client = MultiLLMClient(primary=primary, router=_NoRouter(), temperature=None, max_tokens=None)
    await client.complete(_req())
    assert primary.last_req.max_tokens == 16384


@pytest.mark.asyncio
async def test_llmerror_triggers_fallback():
    primary = _RecordingProvider(name="primary", raises=LLMError("HTTP 400 bad temperature"))
    fallback = _RecordingProvider(name="fallback")
    client = MultiLLMClient(primary=primary, fallback=fallback, router=_NoRouter(), temperature=1.0)
    resp = await client.complete(_req())
    assert resp.id == "fallback"
    assert fallback.calls == 1
    # fallback receives the same prepared request (temperature injected)
    assert fallback.last_req.temperature == 1.0


@pytest.mark.asyncio
async def test_llmerror_reraised_when_no_fallback():
    primary = _RecordingProvider(raises=LLMError("HTTP 400"))
    client = MultiLLMClient(primary=primary, router=_NoRouter())
    with pytest.raises(LLMError):
        await client.complete(_req())


@pytest.mark.asyncio
async def test_ratelimit_still_triggers_fallback():
    primary = _RecordingProvider(raises=LLMRateLimitError("rate limited"))
    fallback = _RecordingProvider(name="fallback")
    client = MultiLLMClient(primary=primary, fallback=fallback, router=_NoRouter())
    resp = await client.complete(_req())
    assert resp.id == "fallback"
