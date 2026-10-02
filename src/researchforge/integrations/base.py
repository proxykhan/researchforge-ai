"""Abstract base class for research providers."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import final

import httpx

from researchforge.integrations.models import SearchQuery, SearchResponse

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
BACKOFF_BASE = 1.0


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out after retries."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider returns a rate-limit response."""


class ResearchProvider(ABC):
    """Interface that every research source must implement."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'arxiv')."""

    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Search for papers matching the query."""

    @final
    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        """Make an HTTP request with exponential backoff retry."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, url, **kwargs)  # type: ignore[arg-type]

                if response.status_code == 429:
                    last_error = ProviderRateLimitError(self.name, "Rate limited")
                    if attempt + 1 >= self.max_retries:
                        break
                    retry_after = float(
                        response.headers.get("Retry-After", BACKOFF_BASE * (2**attempt))
                    )
                    logger.warning(
                        "%s rate-limited, retrying in %.1fs (attempt %d/%d)",
                        self.name,
                        retry_after,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except httpx.TimeoutException as exc:
                wait = BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "%s timeout, retrying in %.1fs (attempt %d/%d)",
                    self.name,
                    wait,
                    attempt + 1,
                    self.max_retries,
                )
                last_error = exc
                await asyncio.sleep(wait)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    wait = BACKOFF_BASE * (2**attempt)
                    logger.warning(
                        "%s server error %d, retrying in %.1fs",
                        self.name,
                        exc.response.status_code,
                        wait,
                    )
                    last_error = exc
                    await asyncio.sleep(wait)
                else:
                    raise ProviderError(self.name, f"HTTP {exc.response.status_code}") from exc

        if isinstance(last_error, httpx.TimeoutException):
            raise ProviderTimeoutError(self.name, "Request timed out after retries") from last_error
        if isinstance(last_error, ProviderRateLimitError):
            raise last_error
        raise ProviderError(self.name, "Request failed after retries")
