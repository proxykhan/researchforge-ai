"""Anthropic LLM provider using the official SDK."""

from __future__ import annotations

import os

import anthropic

from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message, TokenUsage

DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicProvider(LLMProvider):
    """LLM provider backed by the Anthropic Messages API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._default_model = default_model
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config or LLMConfig(model=self._default_model)

        api_messages: list[anthropic.types.MessageParam] = [
            {"role": m.role, "content": m.content}  # type: ignore[typeddict-item]
            for m in messages
        ]

        # temperature is not forwarded: Claude Sonnet 5 and newer reject sampling params with a 400.
        kwargs: dict[str, object] = {}
        if cfg.system:
            kwargs["system"] = cfg.system
        if cfg.stop_sequences:
            kwargs["stop_sequences"] = cfg.stop_sequences

        response = await self._client.messages.create(  # type: ignore[call-overload]
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            messages=api_messages,
            **kwargs,
        )

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            stop_reason=response.stop_reason,
        )
