from collections.abc import AsyncIterator
from typing import ClassVar

from sdlc.llm.anthropic_provider import (
    AnthropicProvider,
    LLMAuthError,
    LLMBadRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from sdlc.llm.models import CompletionRequest, CompletionResponse, ModelInfo
from sdlc.llm.openai_compatible import OpenAICompatibleProvider
from sdlc.llm.openai_provider import OpenAIProvider
from sdlc.utils.exceptions import LLMError


class ModelRouter:
    RULES: ClassVar[dict[str, list[tuple[str, str]]]] = {
        "anthropic": [
            ("high", "claude-opus-4-20250514"),
            ("medium", "claude-sonnet-4-20250514"),
            ("low", "claude-haiku-4-5-20251001"),
        ],
        "openai": [
            ("high", "o1"),
            ("medium", "gpt-4o"),
            ("low", "gpt-4o-mini"),
        ],
    }

    def __init__(
        self,
        provider_type: str = "anthropic",
        default_model: str = "",
        use_tier_routing: bool = True,
    ) -> None:
        self.provider_type = provider_type
        self.default_model = default_model
        self.use_tier_routing = use_tier_routing

    def route(self, req: CompletionRequest) -> str:
        # When tier routing is disabled (e.g. custom proxy/base_url),
        # always use the configured default_model
        if not self.use_tier_routing:
            return self.default_model or "claude-sonnet-4-20250514"

        tier = req.metadata.get("tier", "medium")
        rules = self.RULES.get(self.provider_type, [])
        for t, model in rules:
            if tier == t:
                return model
        return self.default_model or "claude-sonnet-4-20250514"


class MultiLLMClient:
    def __init__(
        self,
        primary: AnthropicProvider | OpenAIProvider | OpenAICompatibleProvider,
        fallback: AnthropicProvider | OpenAIProvider | OpenAICompatibleProvider | None = None,
        router: ModelRouter | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.router = router or ModelRouter()
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _prepare(self, req: CompletionRequest) -> CompletionRequest:
        """Route the model and inject configured defaults for any field the
        caller left unset.

        - ``model`` is rewritten by the router.
        - ``max_tokens`` falls back to the configured value, then a hard
          default (providers require it).
        - ``temperature`` falls back to the configured value; if that is also
          None it stays None and providers omit it entirely (required for
          Anthropic thinking/adaptive gateway models that reject any explicit
          temperature).
        """
        update: dict[str, object] = {}
        actual_model = self.router.route(req)
        if actual_model:
            update["model"] = actual_model
        if req.max_tokens is None:
            update["max_tokens"] = self.max_tokens if self.max_tokens is not None else 16384
        if req.temperature is None and self.temperature is not None:
            update["temperature"] = self.temperature
        return req.model_copy(update=update) if update else req

    def _strip_conflicting_param(
        self, req: CompletionRequest, param: str | None
    ) -> CompletionRequest | None:
        """Return a copy of *req* with the conflicting *param* neutralized, so a
        parameter-rejection 400 can be retried on the *same* provider before
        considering a fallback. Returns None when we can't act on the param
        (unknown, or already unset) — signaling the caller not to blind-retry.
        """
        if param == "temperature" and req.temperature is not None:
            return req.model_copy(update={"temperature": None})
        if param == "top_p" and req.top_p != 1.0:
            return req.model_copy(update={"top_p": 1.0})
        if param == "stop_sequences" and req.stop_sequences:
            return req.model_copy(update={"stop_sequences": []})
        return None

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        prepared = self._prepare(req)
        try:
            return await self.primary.complete(prepared)
        except LLMAuthError:
            # Configuration problem: don't retry, don't fall back — surface it.
            raise
        except LLMBadRequestError as e:
            # Parameter rejection: try fixing it on the same provider once
            # before falling back (a fallback would re-send the same bad param).
            retried = self._strip_conflicting_param(prepared, e.param)
            if retried is not None:
                return await self.primary.complete(retried)
            if self.fallback is not None:
                return await self.fallback.complete(prepared)
            raise
        except (LLMRateLimitError, LLMTimeoutError, LLMError):
            if self.fallback is not None:
                return await self.fallback.complete(prepared)
            raise

    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]:
        prepared = self._prepare(req)
        try:
            async for chunk in self.primary.stream(prepared):
                yield chunk
        except LLMAuthError:
            raise
        except LLMBadRequestError as e:
            # Safe to retry here only because failure occurs before any chunk is
            # yielded (providers raise during request setup, not mid-generation).
            retried = self._strip_conflicting_param(prepared, e.param)
            if retried is not None:
                async for chunk in self.primary.stream(retried):
                    yield chunk
            elif self.fallback is not None:
                async for chunk in self.fallback.stream(prepared):
                    yield chunk
            else:
                raise
        except (LLMRateLimitError, LLMTimeoutError, LLMError):
            if self.fallback is not None:
                async for chunk in self.fallback.stream(prepared):
                    yield chunk
            else:
                raise

    def model_info(self, model: str) -> ModelInfo:
        try:
            return self.primary.model_info(model)
        except Exception:
            if self.fallback is not None:
                return self.fallback.model_info(model)
            raise
