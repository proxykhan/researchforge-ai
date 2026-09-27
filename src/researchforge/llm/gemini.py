"""Google Gemini LLM provider using the official SDK."""

from __future__ import annotations

import asyncio
import os

from google import genai
from google.genai import errors as genai_errors

from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message, TokenUsage

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_RETRIES = 4
RETRY_BASE_DELAY = 5.0


class GeminiProvider(LLMProvider):
    """LLM provider backed by the Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._default_model = default_model
        self._client = genai.Client(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "gemini"

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config or LLMConfig(model=self._default_model)
        model = cfg.model if cfg.model != "claude-sonnet-5" else self._default_model

        contents: list[genai.types.Content] = []
        system_instruction: str | None = cfg.system

        for m in messages:
            if m.role == "system":
                system_instruction = m.content
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append(
                    genai.types.Content(
                        role=role,
                        parts=[genai.types.Part(text=m.content)],
                    )
                )

        gen_config = genai.types.GenerateContentConfig(
            max_output_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            system_instruction=system_instruction,
            stop_sequences=cfg.stop_sequences or None,
        )

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=gen_config,
                )
                break
            except genai_errors.ServerError as exc:
                last_error = exc
                delay = RETRY_BASE_DELAY * (2**attempt)
                await asyncio.sleep(delay)
        else:
            raise last_error  # type: ignore[misc]

        content = response.text or ""
        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0

        finish_reason = None
        if response.candidates and response.candidates[0].finish_reason:
            finish_reason = response.candidates[0].finish_reason.name

        return LLMResponse(
            content=content,
            model=model,
            usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            stop_reason=finish_reason,
        )
