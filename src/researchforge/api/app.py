"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from researchforge import __version__
from researchforge.api.routes import health, research
from researchforge.auth.dependencies import AuthDependency, UserLookup
from researchforge.auth.user_store import InMemoryUserStore
from researchforge.cache.rate_limiter import RateLimiter
from researchforge.cache.redis_client import RedisClient
from researchforge.config import Settings, load_settings
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.anthropic import AnthropicProvider
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig
from researchforge.repositories.base import ResearchRepository
from researchforge.repositories.memory import InMemoryResearchRepository
from researchforge.services.research import ResearchService
from researchforge.workers.manager import JobManager


def _build_lifespan(
    service: ResearchService,
    redis_client: RedisClient | None = None,
) -> Callable[..., Any]:
    """Create a lifespan context manager bound to the given service."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        service.job_manager.start()
        if redis_client is not None:
            await redis_client.connect()
        yield
        if redis_client is not None:
            await redis_client.close()
        await service.job_manager.shutdown()

    return lifespan


def create_app(
    settings: Settings | None = None,
    llm: LLMProvider | None = None,
    registry: ProviderRegistry | None = None,
    job_manager: JobManager | None = None,
    repository: ResearchRepository | None = None,
    user_lookup: UserLookup | None = None,
) -> FastAPI:
    """Build and configure the FastAPI application.

    Parameters are injectable for testing — production uses defaults from env.
    """
    settings = settings or load_settings()

    llm = llm or AnthropicProvider(default_model=settings.llm_model)
    registry = registry or ProviderRegistry()

    llm_config = LLMConfig(model=settings.llm_model)
    manager = job_manager or JobManager()
    repo = repository or InMemoryResearchRepository()
    lookup = user_lookup or InMemoryUserStore()
    service = ResearchService(
        llm=llm,
        registry=registry,
        repository=repo,
        llm_config=llm_config,
        job_manager=manager,
    )

    redis_client: RedisClient | None = None
    rate_limiter: RateLimiter | None = None
    if settings.redis_url:
        redis_client = RedisClient(settings.redis_url)
        rate_limiter = RateLimiter(redis_client)

    auth = AuthDependency(lookup, enabled=settings.auth_enabled)

    app = FastAPI(
        title="ResearchForge AI",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=_build_lifespan(service, redis_client),
    )

    app.state.research_service = service
    app.state.auth_dependency = auth
    app.state.redis_client = redis_client
    app.state.rate_limiter = rate_limiter

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(research.router, prefix="/api/v1")

    return app
