import logging
import time
from collections.abc import AsyncIterator
from typing import Any, ClassVar

import openai

from sdlc.llm.anthropic_provider import (
    LLMAuthError,
    LLMBadRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
    _extract_param,
)
from sdlc.llm.models import (
    CompletionRequest,
    CompletionResponse,
    ContentBlock,
    ModelInfo,
    Usage,
)
from sdlc.llm.pricing import compute_cost
from sdlc.utils.exceptions import LLMError

logger = logging.getLogger(__name__)


class OpenAIProvider:
    PRICING: ClassVar[dict[str, dict[str, float]]] = {
        "gpt-4o": {"in": 5.0, "out": 15.0},
        "gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "o1": {"in": 15.0, "out": 60.0},
        "o1-mini": {"in": 3.0, "out": 12.0},
    }

    def __init__(self, api_key: str, timeout: int = 60) -> None:
        self.client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout)

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        start = time.monotonic()
        try:
            oai_msgs = self._convert_messages(req)
            kwargs: dict[str, Any] = {
                "model": req.model,
                "messages": oai_msgs,
                "max_tokens": req.max_tokens or 16384,
            }
            if req.temperature is not None:
                kwargs["temperature"] = req.temperature
            if req.stop_sequences:
                kwargs["stop"] = req.stop_sequences

            response = await self.client.chat.completions.create(**kwargs)
            return self._to_response(response, start)
        except openai.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except openai.APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except openai.AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except openai.BadRequestError as e:
            raise LLMBadRequestError(str(e), param=_extract_param(str(e))) from e
        except openai.APIError as e:
            raise LLMError(str(e)) from e

    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]:
        try:
            oai_msgs = self._convert_messages(req)
            stream = await self.client.chat.completions.create(
                model=req.model,
                messages=oai_msgs,  # type: ignore[arg-type]
                stream=True,
            )
            async for chunk in stream:  # type: ignore[union-attr]
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except openai.APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except openai.AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except openai.BadRequestError as e:
            raise LLMBadRequestError(str(e), param=_extract_param(str(e))) from e
        except openai.APIError as e:
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
            provider="openai",
            pricing_input_per_m=pricing["in"],
            pricing_output_per_m=pricing["out"],
            max_context=128000,
            max_output=16384,
        )

    def _convert_messages(self, req: CompletionRequest) -> list[dict[str, Any]]:
        msgs = []
        if req.system:
            msgs.append({"role": "system", "content": req.system})
        for m in req.messages:
            if isinstance(m.content, str):
                msgs.append({"role": m.role.value, "content": m.content})
            else:
                text_parts = [b.text for b in m.content if b.type == "text" and b.text]
                msgs.append({"role": m.role.value, "content": "\n".join(text_parts)})
        return msgs

    def _to_response(self, raw: Any, start: float) -> CompletionResponse:
        choice = raw.choices[0] if raw.choices else None
        content_text = choice.message.content if choice else ""
        usage = raw.usage
        cost = 0.0
        cost_source = "exact"
        if usage:
            cost, cost_source = compute_cost(
                raw.model, usage.prompt_tokens, usage.completion_tokens, self.PRICING
            )
            if cost_source == "estimate":
                logger.info(
                    "No pricing data for model '%s'; using conservative estimate "
                    "(cost_usd may be approximate). Add it to PRICING for exact cost.",
                    raw.model,
                )
        return CompletionResponse(
            id=raw.id or "",
            model=raw.model,
            content=[ContentBlock(type="text", text=content_text)],
            stop_reason=choice.finish_reason if choice else "",
            usage=Usage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            ),
            cost_usd=cost,
            cost_source=cost_source,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
