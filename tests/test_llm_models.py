from sdlc.llm.models import (
    CompletionRequest,
    CompletionResponse,
    ContentBlock,
    Message,
    ModelInfo,
    Role,
    Tool,
    Usage,
)


def test_role_enum_values():
    assert len(Role) == 4
    assert Role.SYSTEM == "system"
    assert Role.USER == "user"
    assert Role.ASSISTANT == "assistant"
    assert Role.TOOL == "tool"


def test_message_creation_string_content():
    msg = Message(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"


def test_message_creation_block_content():
    blocks = [ContentBlock(type="text", text="Hi"), ContentBlock(type="text", text="World")]
    msg = Message(role=Role.ASSISTANT, content=blocks)
    assert msg.role == Role.ASSISTANT
    assert len(msg.content) == 2
    assert msg.content[0].text == "Hi"


def test_message_serialization():
    msg = Message(role=Role.USER, content="test")
    data = msg.model_dinternal-monitoring()
    assert data["role"] == "user"
    assert data["content"] == "test"


def test_content_block_text_type():
    block = ContentBlock(type="text", text="some text")
    assert block.type == "text"
    assert block.text == "some text"
    assert block.id is None


def test_content_block_tool_use_type():
    block = ContentBlock(type="tool_use", id="call_123", name="search", input={"q": "test"})
    assert block.type == "tool_use"
    assert block.id == "call_123"
    assert block.name == "search"
    assert block.input == {"q": "test"}


def test_content_block_tool_result_type():
    block = ContentBlock(type="tool_result", tool_call_id="call_123", content="result data")
    assert block.type == "tool_result"
    assert block.tool_call_id == "call_123"
    assert block.content == "result data"


def test_completion_request_defaults():
    req = CompletionRequest()
    assert req.model == "claude-sonnet-4-20250514"
    assert req.messages == []
    assert req.tools == []
    assert req.system is None
    # max_tokens/temperature default to None ("unset"): MultiLLMClient injects
    # the configured values, and providers omit temperature entirely when None.
    assert req.max_tokens is None
    assert req.temperature is None
    assert req.top_p == 1.0
    assert req.stop_sequences == []
    assert req.metadata == {}


def test_completion_request_custom():
    req = CompletionRequest(
        model="claude-opus-4-20250514",
        messages=[Message(role=Role.USER, content="hi")],
        system="You are helpful",
        max_tokens=8192,
        metadata={"tier": "high"},
    )
    assert req.model == "claude-opus-4-20250514"
    assert len(req.messages) == 1
    assert req.system == "You are helpful"
    assert req.max_tokens == 8192
    assert req.metadata["tier"] == "high"


def test_completion_response_creation():
    resp = CompletionResponse(
        id="msg_123",
        model="claude-sonnet-4-20250514",
        content=[ContentBlock(type="text", text="Hello")],
        stop_reason="end_turn",
        usage=Usage(input_tokens=10, output_tokens=20),
        cost_usd=0.001,
        duration_ms=500,
    )
    assert resp.id == "msg_123"
    assert resp.model == "claude-sonnet-4-20250514"
    assert len(resp.content) == 1
    assert resp.content[0].text == "Hello"
    assert resp.stop_reason == "end_turn"
    assert resp.usage.input_tokens == 10
    assert resp.usage.output_tokens == 20
    assert resp.cost_usd == 0.001
    assert resp.duration_ms == 500
    assert resp.cached is False


def test_completion_response_defaults():
    resp = CompletionResponse()
    assert resp.id == ""
    assert resp.model == ""
    assert resp.content == []
    assert resp.stop_reason == ""
    assert resp.cost_usd == 0.0
    assert resp.duration_ms == 0
    assert resp.cached is False


def test_usage_defaults():
    usage = Usage()
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.cache_read_tokens == 0
    assert usage.cache_creation_tokens == 0


def test_usage_custom():
    usage = Usage(input_tokens=100, output_tokens=50, cache_read_tokens=30)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cache_read_tokens == 30


def test_tool_creation():
    tool = Tool(name="search", description="Search the web", input_schema={"type": "object"})
    assert tool.name == "search"
    assert tool.description == "Search the web"
    assert tool.input_schema == {"type": "object"}


def test_model_info_creation():
    info = ModelInfo(
        name="claude-sonnet-4-20250514",
        provider="anthropic",
        pricing_input_per_m=3.0,
        pricing_output_per_m=15.0,
        max_context=200000,
        max_output=8192,
    )
    assert info.name == "claude-sonnet-4-20250514"
    assert info.provider == "anthropic"
    assert info.pricing_input_per_m == 3.0
    assert info.pricing_output_per_m == 15.0
    assert info.max_context == 200000
    assert info.max_output == 8192
