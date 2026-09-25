"""Tests for the Anthropic LLM provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, patch

from researchforge.llm.anthropic import AnthropicProvider
from researchforge.llm.models import LLMConfig, Message


@dataclass
class FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class FakeTextBlock:
    type: str = "text"
    text: str = "The answer is 42."


@dataclass
class FakeResponse:
    content: list[FakeTextBlock]
    model: str = "claude-sonnet-5"
    usage: FakeUsage = field(default_factory=FakeUsage)
    stop_reason: str = "end_turn"


class TestAnthropicProvider:
    def test_name(self):
        provider = AnthropicProvider(api_key="test-key")
        assert provider.name == "anthropic"

    async def test_complete_basic(self):
        provider = AnthropicProvider(api_key="test-key")

        fake_resp = FakeResponse(content=[FakeTextBlock()])
        mock_create = AsyncMock(return_value=fake_resp)

        with patch.object(provider._client.messages, "create", mock_create):
            result = await provider.complete(
                messages=[Message(role="user", content="What is 6 * 7?")],
            )

        assert result.content == "The answer is 42."
        assert result.model == "claude-sonnet-5"
        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50
        assert result.stop_reason == "end_turn"

    async def test_complete_with_config(self):
        provider = AnthropicProvider(api_key="test-key")

        fake_resp = FakeResponse(content=[FakeTextBlock(text="custom response")])
        mock_create = AsyncMock(return_value=fake_resp)

        config = LLMConfig(
            model="claude-opus-5",
            max_tokens=2048,
            system="You are a helpful assistant.",
            stop_sequences=["STOP"],
        )

        with patch.object(provider._client.messages, "create", mock_create):
            result = await provider.complete(
                messages=[Message(role="user", content="hi")],
                config=config,
            )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-5"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["system"] == "You are a helpful assistant."
        assert call_kwargs["stop_sequences"] == ["STOP"]
        assert result.content == "custom response"

    async def test_complete_multiple_text_blocks(self):
        provider = AnthropicProvider(api_key="test-key")

        fake_resp = FakeResponse(
            content=[FakeTextBlock(text="Part 1. "), FakeTextBlock(text="Part 2.")]
        )
        mock_create = AsyncMock(return_value=fake_resp)

        with patch.object(provider._client.messages, "create", mock_create):
            result = await provider.complete(
                messages=[Message(role="user", content="test")],
            )

        assert result.content == "Part 1. Part 2."

    async def test_default_model_from_constructor(self):
        provider = AnthropicProvider(api_key="test-key", default_model="claude-opus-5")

        fake_resp = FakeResponse(content=[FakeTextBlock()])
        mock_create = AsyncMock(return_value=fake_resp)

        with patch.object(provider._client.messages, "create", mock_create):
            await provider.complete(messages=[Message(role="user", content="test")])

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-5"
