"""Groq Cloud LLM provider using their OpenAI-compatible API."""

from __future__ import annotations

import asyncio
import os

import httpx

from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message, TokenUsage

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 4
RETRY_BASE_DELAY = 2.0
API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    """LLM provider backed by the Groq Cloud API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "groq"

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config or LLMConfig(model=self._default_model)
        model = cfg.model if cfg.model not in ("claude-sonnet-5", "gemini-3.8-flash") else self._default_model

        openai_messages: list[dict[str, str]] = []
        for m in messages:
            openai_messages.append({"role": m.role, "content": m.content})

        if cfg.system and not any(m["role"] == "system" for m in openai_messages):
            openai_messages.insert(0, {"role": "system", "content": cfg.system})

        payload: dict = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
        }
        if cfg.stop_sequences:
            payload["stop"] = cfg.stop_sequences

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(API_URL, json=payload, headers=headers)
                    if resp.status_code == 429:
                        last_error = Exception(f"429 Rate limited: {resp.text}")
                        delay = RETRY_BASE_DELAY * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                break
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    last_error = exc
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise
        else:
            raise last_error  # type: ignore[misc]

        choice = data["choices"][0]
        content = choice["message"]["content"] or ""
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", model),
            usage=TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            ),
            stop_reason=choice.get("finish_reason"),
        )
