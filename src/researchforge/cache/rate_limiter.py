"""Fixed-window rate limiter backed by Redis.

Each user gets ``max_requests`` per ``window_seconds``.  The limiter
uses Redis INCR + EXPIRE so the window resets automatically.

When Redis is unavailable the limiter is permissive — requests go through
rather than blocking the entire API.
"""

from __future__ import annotations

from researchforge.cache.redis_client import RedisClient

DEFAULT_MAX_REQUESTS = 60
DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    """Per-user fixed-window rate limiter."""

    def __init__(
        self,
        redis: RedisClient,
        *,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._redis = redis
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def check(self, user_id: str) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        if not self._redis.available:
            return True

        key = f"ratelimit:{user_id}"
        count = await self._redis.incr(key)

        if count == 1:
            await self._redis.expire(key, self._window_seconds)

        return count <= self._max_requests
