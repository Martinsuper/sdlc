"""Tests for MultiLLMClient exception routing (Q0 §3.3).

Distinguishes three 4xx-class failure modes so we don't blindly fail over:
  - LLMAuthError (401/403): surface, no retry, no fallback.
  - LLMBadRequestError (param 400): strip the offending param and retry the
    SAME provider once before considering fallback.
  - rate-limit / timeout / generic LLMError: fall back (unchanged behavior).
"""

from __future__ import annotations

import pytest

from sdlc.llm.anthropic_provider import (
    LLMAuthError,
    LLMBadRequestError,
    LLMRateLimitError,
)
from sdlc.llm.client import MultiLLMClient
from sdlc.llm.models import CompletionRequest, CompletionResponse, Message, Role
from sdlc.utils.exceptions import LLMError


class _RecordingProvider:
    """Returns a trivial response, recording every request it receives."""

    def __init__(self, name: str = "primary", raises: Exception | None = None) -> None:
        self.name = name
        self.raises = raises
        self.reqs: list[CompletionRequest] = []

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        self.reqs.append(req)
        if self.raises is not None:
            raise self.raises
        return CompletionResponse(id=self.name, model=req.model, content=[])

    @property
    def calls(self) -> int:
        return len(self.reqs)


class _BadThenOkProvider:
    """Raises LLMBadRequestError(param) on the first call, succeeds after."""

    def __init__(self, param: str) -> None:
        self.param = param
        self.reqs: list[CompletionRequest] = []

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        self.reqs.append(req)
        if len(self.reqs) == 1:
            raise LLMBadRequestError("400 invalid temperature", param=self.param)
        return CompletionResponse(id="primary", model=req.model, content=[])


class _NoRouter:
    def route(self, req: CompletionRequest) -> str | None:
        return None


def _req(**kw) -> CompletionRequest:
    return CompletionRequest(messages=[Message(role=Role.USER, content="hi")], **kw)


@pytest.mark.asyncio
async def test_bad_request_strips_param_and_retries_same_provider():
    primary = _BadThenOkProvider(param="temperature")
    fallback = _RecordingProvider(name="fallback")
    client = MultiLLMClient(
        primary=primary, fallback=fallback, router=_NoRouter(), temperature=0.7
    )
    resp = await client.complete(_req())
    # Retried on primary (not fallback), and the retry omitted temperature.
    assert resp.id == "primary"
    assert len(primary.reqs) == 2
    assert primary.reqs[0].temperature == 0.7
    assert primary.reqs[1].temperature is None
    assert fallback.calls == 0  # fallback must NOT be used for a fixable 400


@pytest.mark.asyncio
async def test_bad_request_unactionable_param_falls_back():
    # param the client can't strip (already unset / unknown) => use fallback.
    primary = _RecordingProvider(
        raises=LLMBadRequestError("400 model not found", param=None)
    )
    fallback = _RecordingProvider(name="fallback")
    client = MultiLLMClient(primary=primary, fallback=fallback, router=_NoRouter())
    resp = await client.complete(_req())
    assert resp.id == "fallback"
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_bad_request_no_fallback_reraises():
    primary = _RecordingProvider(
        raises=LLMBadRequestError("400 model not found", param=None)
    )
    client = MultiLLMClient(primary=primary, router=_NoRouter())
    with pytest.raises(LLMBadRequestError):
        await client.complete(_req())


@pytest.mark.asyncio
async def test_auth_error_surfaces_without_fallback():
    primary = _RecordingProvider(raises=LLMAuthError("401 invalid api key"))
    fallback = _RecordingProvider(name="fallback")
    client = MultiLLMClient(primary=primary, fallback=fallback, router=_NoRouter())
    with pytest.raises(LLMAuthError):
        await client.complete(_req())
    assert fallback.calls == 0  # never fall back on an auth/config problem


@pytest.mark.asyncio
async def test_rate_limit_still_falls_back():
    # Regression: unchanged behavior for rate-limit.
    primary = _RecordingProvider(raises=LLMRateLimitError("429"))
    fallback = _RecordingProvider(name="fallback")
    client = MultiLLMClient(primary=primary, fallback=fallback, router=_NoRouter())
    resp = await client.complete(_req())
    assert resp.id == "fallback"


@pytest.mark.asyncio
async def test_generic_llmerror_still_falls_back():
    # Regression: plain LLMError (non-400-subclass) keeps falling back.
    primary = _RecordingProvider(raises=LLMError("connection reset"))
    fallback = _RecordingProvider(name="fallback")
    client = MultiLLMClient(primary=primary, fallback=fallback, router=_NoRouter())
    resp = await client.complete(_req())
    assert resp.id == "fallback"
