"""LLM connectivity smoke test.

Shared helper used by `sdlc doctor`, `sdlc llm test`, and `sdlc config
test-llm` to actually exercise the configured provider with a tiny real
completion request — rather than only checking that the provider object can be
constructed (which makes no network call and hides runtime errors such as bad
credentials or gateway parameter rejections).
"""

from __future__ import annotations

import os

from sdlc.cli.deps import build_llm_client
from sdlc.llm.models import CompletionRequest, Message, Role
from sdlc.utils.async_runner import run_with_timeout
from sdlc.utils.config import LLMConfig, SdlcConfig


async def _probe(cfg: LLMConfig, timeout: float) -> str:
    client = build_llm_client(cfg)
    req = CompletionRequest(
        model=cfg.model,
        messages=[Message(role=Role.USER, content="ping")],
        max_tokens=8,
    )
    resp = await run_with_timeout(client.complete(req), timeout=timeout)
    return resp.model or cfg.model


def smoke_test(config: LLMConfig | SdlcConfig, timeout: float = 30.0) -> tuple[bool, str]:
    """Send one minimal completion to verify end-to-end connectivity.

    Returns ``(ok, detail)``. ``ok`` is False (not an exception) for the common
    "API key not set" case so callers can render it as SKIP rather than FAIL.
    """
    import asyncio

    llm_cfg = config.llm if isinstance(config, SdlcConfig) else config

    if llm_cfg.api_key_env and not os.environ.get(llm_cfg.api_key_env, ""):
        return False, f"API key not set ({llm_cfg.api_key_env})"

    try:
        model = asyncio.run(_probe(llm_cfg, timeout))
        return True, f"reachable (model={model})"
    except Exception as e:
        return False, str(e)
