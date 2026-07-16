"""Tests for OpenAICompatibleProvider."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sdlc.llm.models import CompletionRequest, ContentBlock, Message, Role
from sdlc.llm.openai_compatible import OpenAICompatibleProvider


def test_construction_with_custom_base_url():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        provider_name="deepseek",
    )
    assert provider.provider_name == "deepseek"


def test_model_info_deepseek():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        provider_name="deepseek",
    )
    info = provider.model_info("deepseek-chat")
    assert info.name == "deepseek-chat"
    assert info.provider == "deepseek"
    assert info.pricing_input_per_m == 0.14
    assert info.pricing_output_per_m == 0.28
    assert info.max_context == 131072  # deepseek in name -> 131072


def test_model_info_qwen():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        provider_name="qwen",
    )
    info = provider.model_info("qwen-plus")
    assert info.name == "qwen-plus"
    assert info.pricing_input_per_m == 0.8
    assert info.pricing_output_per_m == 2.0
    assert info.max_context == 131072  # qwen in name -> 131072


def test_model_info_moonshot_8k():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://api.moonshot.cn/v1",
        provider_name="moonshot",
    )
    info = provider.model_info("moonshot-v1-8k")
    assert info.name == "moonshot-v1-8k"
    assert info.pricing_input_per_m == 1.0
    assert info.pricing_output_per_m == 1.0
    assert info.max_context == 8192  # 8k in name


def test_model_info_moonshot_128k():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://api.moonshot.cn/v1",
        provider_name="moonshot",
    )
    info = provider.model_info("moonshot-v1-128k")
    assert info.max_context == 131072  # 128k in name


def test_model_info_glm():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        provider_name="glm",
    )
    info = provider.model_info("glm-4")
    assert info.pricing_input_per_m == 1.0
    assert info.pricing_output_per_m == 1.0
    assert info.max_context == 128000  # default


def test_model_info_glm_long():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        provider_name="glm",
    )
    info = provider.model_info("glm-4-long")
    assert info.max_context == 1000000  # long in name


def test_model_info_ollama_llama3():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="http://localhost:11434/v1",
        provider_name="ollama",
    )
    info = provider.model_info("llama3")
    assert info.pricing_input_per_m == 0.0
    assert info.pricing_output_per_m == 0.0
    assert info.max_context == 8192  # llama3 in name


def test_model_info_siliconflow():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://api.siliconflow.cn/v1",
        provider_name="siliconflow",
    )
    info = provider.model_info("Qwen/Qwen2.5-72B-Instruct")
    assert info.pricing_input_per_m == 0.42
    assert info.pricing_output_per_m == 0.42


def test_model_info_unknown_model():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://example.com/v1",
        provider_name="custom",
    )
    info = provider.model_info("custom-model")
    assert info.pricing_input_per_m == 0.0
    assert info.pricing_output_per_m == 0.0
    assert info.max_context == 128000  # default


def test_model_info_32k_in_name():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://example.com/v1",
    )
    info = provider.model_info("moonshot-v1-32k")
    assert info.max_context == 32768


@pytest.mark.asyncio
async def test_complete_with_mocked_client():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        provider_name="deepseek",
    )

    # Mock the response
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello from DeepSeek!"
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20

    mock_response = MagicMock()
    mock_response.id = "chatcmpl-123"
    mock_response.model = "deepseek-chat"
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    provider.client = MagicMock()
    provider.client.chat = MagicMock()
    provider.client.chat.completions = MagicMock()
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

    req = CompletionRequest(
        model="deepseek-chat",
        messages=[Message(role=Role.USER, content="Hi")],
    )
    resp = await provider.complete(req)

    assert resp.id == "chatcmpl-123"
    assert resp.model == "deepseek-chat"
    assert len(resp.content) == 1
    assert resp.content[0].text == "Hello from DeepSeek!"
    assert resp.stop_reason == "stop"
    assert resp.usage.input_tokens == 10
    assert resp.usage.output_tokens == 20
    # Cost: (10 * 0.14 + 20 * 0.28) / 1_000_000
    expected_cost = (10 * 0.14 + 20 * 0.28) / 1_000_000
    assert abs(resp.cost_usd - expected_cost) < 1e-10
    assert resp.duration_ms >= 0


@pytest.mark.asyncio
async def test_stream_with_mocked_client():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        provider_name="deepseek",
    )

    # Create mock chunks
    async def mock_stream():
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " World"

        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None

        for chunk in [chunk1, chunk2, chunk3]:
            yield chunk

    provider.client = MagicMock()
    provider.client.chat = MagicMock()
    provider.client.chat.completions = MagicMock()
    provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

    req = CompletionRequest(
        model="deepseek-chat",
        messages=[Message(role=Role.USER, content="Hi")],
    )

    chunks = []
    async for text in provider.stream(req):
        chunks.append(text)

    assert chunks == ["Hello", " World"]


def test_convert_messages_with_system():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://example.com/v1",
    )
    req = CompletionRequest(
        system="You are a helper.",
        messages=[Message(role=Role.USER, content="Hi")],
    )
    msgs = provider._convert_messages(req)
    assert len(msgs) == 2
    assert msgs[0] == {"role": "system", "content": "You are a helper."}
    assert msgs[1] == {"role": "user", "content": "Hi"}


def test_convert_messages_with_content_blocks():
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="https://example.com/v1",
    )
    req = CompletionRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    ContentBlock(type="text", text="Hello"),
                    ContentBlock(type="text", text="World"),
                ],
            )
        ],
    )
    msgs = provider._convert_messages(req)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Hello\nWorld"
