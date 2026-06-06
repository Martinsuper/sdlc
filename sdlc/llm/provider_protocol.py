"""LLM Provider Protocol - abstract interface for all LLM providers."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from sdlc.llm.models import CompletionRequest, CompletionResponse, ModelInfo


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers must implement."""

    async def complete(self, req: CompletionRequest) -> CompletionResponse: ...
    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]: ...
    def model_info(self, model: str) -> ModelInfo: ...
