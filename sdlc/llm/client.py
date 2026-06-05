from collections.abc import AsyncIterator
from typing import ClassVar

from sdlc.llm.anthropic_provider import AnthropicProvider, LLMRateLimitError, LLMTimeoutError
from sdlc.llm.models import CompletionRequest, CompletionResponse, ModelInfo
from sdlc.llm.openai_provider import OpenAIProvider


class ModelRouter:
    RULES: ClassVar[list[tuple[str, str]]] = [
        ("high", "claude-opus-4-20250514"),
        ("medium", "claude-sonnet-4-20250514"),
        ("low", "claude-haiku-4-5-20251001"),
    ]

    def route(self, req: CompletionRequest) -> str:
        tier = req.metadata.get("tier", "medium")
        for t, model in self.RULES:
            if tier == t:
                return model
        return "claude-sonnet-4-20250514"


class MultiLLMClient:
    def __init__(
        self,
        primary: AnthropicProvider,
        fallback: OpenAIProvider,
        router: ModelRouter | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.router = router or ModelRouter()

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        actual_model = self.router.route(req)
        req.model = actual_model
        try:
            return await self.primary.complete(req)
        except (LLMRateLimitError, LLMTimeoutError):
            return await self.fallback.complete(req)

    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]:
        actual_model = self.router.route(req)
        req.model = actual_model
        async for chunk in self.primary.stream(req):
            yield chunk

    def model_info(self, model: str) -> ModelInfo:
        try:
            return self.primary.model_info(model)
        except Exception:
            return self.fallback.model_info(model)
