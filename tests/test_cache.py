"""Tests for Redis client wrapper and rate limiter."""

from __future__ import annotations

from researchforge.cache.rate_limiter import RateLimiter
from researchforge.cache.redis_client import RedisClient


class FakeRedisClient(RedisClient):
    """In-memory fake for testing without a real Redis server."""

    def __init__(self) -> None:
        super().__init__("")
        self._store: dict[str, int] = {}
        self._is_available = True

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    @property
    def available(self) -> bool:
        return self._is_available

    async def incr(self, key: str) -> int:
        if not self._is_available:
            return 0
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    async def expire(self, key: str, seconds: int) -> None:
        pass

    async def ping(self) -> bool:
        return self._is_available


class TestRedisClient:
    async def test_unavailable_when_no_url(self):
        client = RedisClient("")
        await client.connect()
        assert client.available is False

    async def test_get_returns_none_when_unavailable(self):
        client = RedisClient("")
        await client.connect()
        assert await client.get("key") is None

    async def test_set_noop_when_unavailable(self):
        client = RedisClient("")
        await client.connect()
        await client.set("key", "value")

    async def test_ping_returns_false_when_unavailable(self):
        client = RedisClient("")
        await client.connect()
        assert await client.ping() is False


class TestRateLimiter:
    async def test_allows_under_limit(self):
        redis = FakeRedisClient()
        limiter = RateLimiter(redis, max_requests=5, window_seconds=60)

        for _ in range(5):
            assert await limiter.check("user1") is True

    async def test_blocks_over_limit(self):
        redis = FakeRedisClient()
        limiter = RateLimiter(redis, max_requests=3, window_seconds=60)

        for _ in range(3):
            await limiter.check("user1")

        assert await limiter.check("user1") is False

    async def test_separate_users_have_separate_limits(self):
        redis = FakeRedisClient()
        limiter = RateLimiter(redis, max_requests=2, window_seconds=60)

        assert await limiter.check("alice") is True
        assert await limiter.check("alice") is True
        assert await limiter.check("alice") is False

        assert await limiter.check("bob") is True

    async def test_permissive_when_redis_unavailable(self):
        redis = FakeRedisClient()
        redis._is_available = False
        limiter = RateLimiter(redis, max_requests=1, window_seconds=60)

        assert await limiter.check("user1") is True
        assert await limiter.check("user1") is True
