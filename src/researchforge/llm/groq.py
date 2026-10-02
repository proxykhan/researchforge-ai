"""Groq Cloud LLM provider using their OpenAI-compatible API."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time

import httpx

from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message, TokenUsage

DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_RETRIES = 10
RETRY_BASE_DELAY = 2.0
API_URL = "https://api.groq.com/openai/v1/chat/completions"
FREE_TIER_MAX_TOKENS = 1024
FREE_TIER_TPM = 8000
MIN_REQUEST_INTERVAL = 3.0

_RETRY_AFTER_RE = re.compile(r"try again in (\d+(?:\.\d+)?)s")

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """LLM provider backed by the Groq Cloud API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self._default_model = default_model
        self._last_request_time: float = 0.0

    @property
    def name(self) -> str:
        return "groq"

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config or LLMConfig(model=self._default_model)
        model = (
            cfg.model
            if cfg.model not in ("claude-sonnet-5", "gemini-3.8-flash", "llama-3.3-70b-versatile")
            else self._default_model
        )

        capped_max_tokens = min(cfg.max_tokens, FREE_TIER_MAX_TOKENS)

        openai_messages: list[dict[str, str]] = []
        for m in messages:
            openai_messages.append({"role": m.role, "content": m.content})

        if cfg.system and not any(m["role"] == "system" for m in openai_messages):
            openai_messages.insert(0, {"role": "system", "content": cfg.system})

        payload: dict[str, object] = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": capped_max_tokens,
            "temperature": cfg.temperature,
        }
        if cfg.stop_sequences:
            payload["stop"] = cfg.stop_sequences
        if model.startswith("openai/gpt-oss"):
            # Reasoning tokens share the 1024-token completion cap; at the default effort
            # they can consume it and truncate the JSON/answer the agents need.
            payload["reasoning_effort"] = "low"
            payload["include_reasoning"] = False

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                self._last_request_time = time.monotonic()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(API_URL, json=payload, headers=headers)
                    if resp.status_code == 429:
                        last_error = Exception(f"429 Rate limited: {resp.text}")
                        delay = _parse_retry_after(resp.text, RETRY_BASE_DELAY * (2**attempt))
                        await asyncio.sleep(delay)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                break
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    last_error = exc
                    delay = RETRY_BASE_DELAY * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise
        else:
            raise last_error  # type: ignore[misc]

        choice = data["choices"][0]
        content = choice["message"]["content"] or ""
        usage = data.get("usage", {})
        if choice.get("finish_reason") == "length":
            logger.warning(
                "Groq response truncated at %d completion tokens (model=%s)",
                capped_max_tokens,
                model,
            )

        return LLMResponse(
            content=content,
            model=data.get("model", model),
            usage=TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            ),
            stop_reason=choice.get("finish_reason"),
        )


def _parse_retry_after(body: str, fallback: float) -> float:
    """Extract wait time from Groq's rate-limit error message."""
    match = _RETRY_AFTER_RE.search(body)
    if match:
        return float(match.group(1)) + 1.0
    return fallback
