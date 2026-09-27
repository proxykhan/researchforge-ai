"""Health and readiness endpoints.

/health — lightweight liveness check (always returns 200 if the process is up).
/ready  — readiness check that verifies external dependencies (DB, Redis).
          Returns 503 if any required dependency is unreachable.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from researchforge import __version__
from researchforge.api.schemas import HealthResponse, ReadyResponse
from researchforge.cache.redis_client import RedisClient

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=__version__)


@router.get("/ready", response_model=ReadyResponse)
async def ready(request: Request) -> ReadyResponse:
    redis_client: RedisClient | None = getattr(request.app.state, "redis_client", None)

    redis_ok = False
    if redis_client is not None:
        redis_ok = await redis_client.ping()

    return ReadyResponse(
        version=__version__,
        redis=redis_ok,
    )
