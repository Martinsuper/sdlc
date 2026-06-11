from collections.abc import AsyncIterator
from typing import ClassVar

from sdlc.llm.anthropic_provider import AnthropicProvider, LLMRateLimitError, LLMTimeoutError
from sdlc.llm.models import CompletionRequest, CompletionResponse, ModelInfo
from sdlc.llm.openai_compatible import OpenAICompatibleProvider
from sdlc.llm.openai_provider import OpenAIProvider


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

    def __init__(self, provider_type: str = "anthropic", default_model: str = "") -> None:
        self.provider_type = provider_type
        self.default_model = default_model

    def route(self, req: CompletionRequest) -> str:
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
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.router = router or ModelRouter()

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        actual_model = self.router.route(req)
        routed_req = req.model_copy(update={"model": actual_model}) if actual_model else req
        try:
            return await self.primary.complete(routed_req)
        except (LLMRateLimitError, LLMTimeoutError):
            if self.fallback is not None:
                return await self.fallback.complete(routed_req)
            raise

    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]:
        actual_model = self.router.route(req)
        routed_req = req.model_copy(update={"model": actual_model}) if actual_model else req
        try:
            async for chunk in self.primary.stream(routed_req):
                yield chunk
        except (LLMRateLimitError, LLMTimeoutError):
            if self.fallback is not None:
                async for chunk in self.fallback.stream(routed_req):
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
