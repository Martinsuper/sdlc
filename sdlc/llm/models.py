from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ContentBlock(BaseModel):
    type: str
    text: str | None = None
    id: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None
    tool_call_id: str | None = None
    content: str | None = None


class Message(BaseModel):
    role: Role
    content: str | list[ContentBlock]
    tool_call_id: str | None = None
    name: str | None = None


class Tool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


class CompletionRequest(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    messages: list[Message] = []
    tools: list[Tool] = []
    system: str | None = None
    max_tokens: int = 16384
    temperature: float = 0.7
    top_p: float = 1.0
    stop_sequences: list[str] = []
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompletionResponse(BaseModel):
    id: str = ""
    model: str = ""
    content: list[ContentBlock] = []
    stop_reason: str = ""
    # NOTE: In streaming mode, usage and cost_usd must still be populated.
    # Stream providers should accumulate token counts from stream events and
    # compute cost_usd before returning the final CompletionResponse.
    # Leaving these as zero defeats budget tracking and cost visibility.
    usage: Usage = Field(default_factory=Usage)
    cost_usd: float = 0.0
    duration_ms: int = 0
    cached: bool = False


class ModelInfo(BaseModel):
    name: str
    provider: str
    pricing_input_per_m: float
    pricing_output_per_m: float
    max_context: int
    max_output: int
