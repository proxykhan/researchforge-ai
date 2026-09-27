"""Async Redis client wrapper.

Provides a thin abstraction over the redis.asyncio client so the rest of
the codebase does not depend on the Redis library directly.  The wrapper
also handles graceful degradation — if Redis is unavailable, operations
silently no-op rather than crashing the API.
"""

from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client with connection management."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        if not self._url:
            logger.info("Redis URL not configured — caching disabled")
            return
        self._client = aioredis.from_url(
            self._url,
            decode_responses=False,
            socket_connect_timeout=5,
        )
        try:
            await self._client.ping()
            logger.info("Redis connected at %s", self._url)
        except Exception:
            logger.warning("Redis unavailable — caching disabled")
            self._client = None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def get(self, key: str) -> bytes | None:
        if self._client is None:
            return None
        try:
            result: Any = await self._client.get(key)
            return result  # type: ignore[no-any-return]
        except Exception:
            logger.warning("Redis GET failed for key %s", key)
            return None

    async def set(self, key: str, value: str | bytes, *, expire_seconds: int | None = None) -> None:
        if self._client is None:
            return
        try:
            await self._client.set(key, value, ex=expire_seconds)
        except Exception:
            logger.warning("Redis SET failed for key %s", key)

    async def incr(self, key: str) -> int:
        """Increment a counter, returning its new value."""
        if self._client is None:
            return 0
        try:
            result: Any = await self._client.incr(key)
            return int(result)
        except Exception:
            logger.warning("Redis INCR failed for key %s", key)
            return 0

    async def expire(self, key: str, seconds: int) -> None:
        if self._client is None:
            return
        try:
            await self._client.expire(key, seconds)
        except Exception:
            logger.warning("Redis EXPIRE failed for key %s", key)

    async def delete(self, key: str) -> None:
        if self._client is None:
            return
        try:
            await self._client.delete(key)
        except Exception:
            logger.warning("Redis DELETE failed for key %s", key)

    async def ping(self) -> bool:
        """Check if Redis is reachable."""
        if self._client is None:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            return False
