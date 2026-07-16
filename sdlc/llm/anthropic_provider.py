import logging
import time
from collections.abc import AsyncIterator
from typing import Any, ClassVar

import anthropic

from sdlc.llm.models import (
    CompletionRequest,
    CompletionResponse,
    ContentBlock,
    ModelInfo,
    Role,
    Usage,
)
from sdlc.llm.pricing import compute_cost
from sdlc.utils.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMRateLimitError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMBadRequestError(LLMError):
    """4xx request/parameter error. May be fixable by adjusting a parameter on
    the same provider, so callers should not blindly fail over to a fallback
    provider (which would just re-send the same bad request)."""

    def __init__(self, message: str, *, param: str | None = None) -> None:
        super().__init__(message)
        self.param = param  # conflicting field name if identifiable, e.g. "temperature"


class LLMAuthError(LLMError):
    """401/403 authentication error. A configuration problem — do not retry,
    do not fall back; let it surface so the user fixes their credentials."""


# Parameter names we know how to "strip and retry" at the client layer.
_KNOWN_PARAMS = ("temperature", "top_p", "max_tokens", "stop_sequences")


def _extract_param(message: str) -> str | None:
    """Best-effort: pull the offending parameter name from a 400 error body.

    Returns a known param name if one is mentioned, else None (so the client
    layer won't attempt a blind same-provider retry it can't act on)."""
    lowered = message.lower()
    for param in _KNOWN_PARAMS:
        if param in lowered:
            return param
    return None


class AnthropicProvider:
    PRICING: ClassVar[dict[str, dict[str, float]]] = {
        "claude-opus-4-20250514": {"in": 15.0, "out": 75.0},
        "claude-sonnet-4-20250514": {"in": 3.0, "out": 15.0},
        "claude-haiku-4-5-20251001": {"in": 0.80, "out": 4.0},
    }

    def __init__(self, api_key: str, timeout: int = 60) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        start = time.monotonic()
        try:
            messages = [m for m in req.messages if m.role != Role.SYSTEM]
            raw_msgs = []
            for m in messages:
                msg_dict: dict[str, Any] = {"role": m.role.value}
                if isinstance(m.content, str):
                    msg_dict["content"] = m.content
                else:
                    msg_dict["content"] = [b.model_dinternal-monitoring(exclude_none=True) for b in m.content]
                if m.tool_call_id:
                    msg_dict["tool_call_id"] = m.tool_call_id
                if m.name:
                    msg_dict["name"] = m.name
                raw_msgs.append(msg_dict)

            tools_param = [t.model_dinternal-monitoring() for t in req.tools] or None
            kwargs: dict[str, Any] = {
                "model": req.model,
                "max_tokens": req.max_tokens or 16384,
                "messages": raw_msgs,
                "tools": tools_param,
            }
            if req.temperature is not None:
                kwargs["temperature"] = req.temperature
            if req.system:
                kwargs["system"] = req.system
            if req.stop_sequences:
                kwargs["stop_sequences"] = req.stop_sequences

            response = await self.client.messages.create(**kwargs)
            return self._to_response(response, start)
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except anthropic.AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except anthropic.BadRequestError as e:
            raise LLMBadRequestError(str(e), param=_extract_param(str(e))) from e
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e

    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]:
        try:
            messages = [m for m in req.messages if m.role != Role.SYSTEM]
            raw_msgs = []
            for m in messages:
                msg_dict: dict[str, Any] = {"role": m.role.value}
                if isinstance(m.content, str):
                    msg_dict["content"] = m.content
                else:
                    msg_dict["content"] = [b.model_dinternal-monitoring(exclude_none=True) for b in m.content]
                if m.tool_call_id:
                    msg_dict["tool_call_id"] = m.tool_call_id
                if m.name:
                    msg_dict["name"] = m.name
                raw_msgs.append(msg_dict)

            kwargs: dict[str, Any] = {
                "model": req.model,
                "max_tokens": req.max_tokens or 16384,
                "messages": raw_msgs,
            }
            if req.temperature is not None:
                kwargs["temperature"] = req.temperature
            if req.system:
                kwargs["system"] = req.system
            if req.stop_sequences:
                kwargs["stop_sequences"] = req.stop_sequences
            tools_param = [t.model_dinternal-monitoring() for t in req.tools] or None
            if tools_param:
                kwargs["tools"] = tools_param

            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except anthropic.AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except anthropic.BadRequestError as e:
            raise LLMBadRequestError(str(e), param=_extract_param(str(e))) from e
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e

    def model_info(self, model: str) -> ModelInfo:
        pricing = self.PRICING.get(model)
        if pricing is None:
            logger.warning(
                "No pricing data for model '%s'; cost_usd will be 0. "
                "Consider updating PRICING dict or releasing a new version.",
                model,
            )
            pricing = {"in": 0.0, "out": 0.0}
        return ModelInfo(
            name=model,
            provider="anthropic",
            pricing_input_per_m=pricing["in"],
            pricing_output_per_m=pricing["out"],
            max_context=200000,
            max_output=8192,
        )

    def _to_response(self, raw: Any, start: float) -> CompletionResponse:
        usage = raw.usage
        cost, cost_source = compute_cost(
            raw.model, usage.input_tokens, usage.output_tokens, self.PRICING
        )
        if cost_source == "estimate":
            logger.info(
                "No pricing data for model '%s'; using conservative estimate "
                "(cost_usd may be approximate). Add it to PRICING for exact cost.",
                raw.model,
            )
        content_blocks = []
        for b in raw.content:
            if b.type == "text":
                content_blocks.append(ContentBlock(type="text", text=b.text))
            elif b.type == "tool_use":
                content_blocks.append(
                    ContentBlock(type="tool_use", id=b.id, name=b.name, input=b.input)
                )
        return CompletionResponse(
            id=raw.id,
            model=raw.model,
            content=content_blocks,
            stop_reason=raw.stop_reason,
            usage=Usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0),
                cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0),
            ),
            cost_usd=cost,
            cost_source=cost_source,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
