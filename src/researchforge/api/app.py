"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from researchforge import __version__
from researchforge.api.routes import auth, health, research
from researchforge.auth.dependencies import AuthDependency, UserLookup
from researchforge.auth.user_store import InMemoryUserStore
from researchforge.cache.rate_limiter import RateLimiter
from researchforge.cache.redis_client import RedisClient
from researchforge.config import Settings, load_settings
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig
from researchforge.observability.logging import setup_logging
from researchforge.observability.middleware import RequestIDMiddleware, RequestSizeLimitMiddleware
from researchforge.observability.security import SecurityHeadersMiddleware, cors_config
from researchforge.observability.tracing import setup_tracing
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

    # ── Observability bootstrap ──────────────────────────────────
    setup_logging(
        json=settings.is_production,
        level=settings.log_level,
    )
    setup_tracing(
        otlp_endpoint=settings.otlp_endpoint,
        console=settings.otel_console,
        environment=settings.app_env,
    )

    if llm is None:
        if settings.llm_provider == "groq":
            from researchforge.llm.groq import GroqProvider

            llm = GroqProvider(default_model=settings.llm_model)
        elif settings.llm_provider == "gemini":
            from researchforge.llm.gemini import GeminiProvider

            llm = GeminiProvider(default_model=settings.llm_model)
        else:
            from researchforge.llm.anthropic import AnthropicProvider

            llm = AnthropicProvider(default_model=settings.llm_model)
    registry = registry or ProviderRegistry()

    llm_config = LLMConfig(model=settings.llm_model)
    manager = job_manager or JobManager()

    # ── Database-backed stores when DATABASE_URL is configured ──
    session_factory = None
    pg_user_store = None
    if settings.database_url:
        from researchforge.auth.postgres_user_store import PostgresUserStore
        from researchforge.database.engine import build_engine, build_session_factory
        from researchforge.repositories.postgres import PostgresResearchRepository

        engine = build_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )
        session_factory = build_session_factory(engine)
        pg_user_store = PostgresUserStore(session_factory)

    repo = repository or (
        PostgresResearchRepository(session_factory)
        if session_factory is not None
        else InMemoryResearchRepository()
    )
    lookup = user_lookup or (pg_user_store if pg_user_store is not None else InMemoryUserStore())
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

    auth_dep = AuthDependency(lookup, enabled=settings.auth_enabled)

    app = FastAPI(
        title="ResearchForge AI",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=_build_lifespan(service, redis_client),
    )

    # ── Middleware (outermost first) ─────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)
    app.add_middleware(RequestIDMiddleware)
    _cors = cors_config(allow_origins=settings.cors_origin_list)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors.allow_origins,
        allow_credentials=_cors.allow_credentials,
        allow_methods=_cors.allow_methods,
        allow_headers=_cors.allow_headers,
        expose_headers=_cors.expose_headers,
    )

    app.state.research_service = service
    app.state.auth_dependency = auth_dep
    app.state.redis_client = redis_client
    app.state.rate_limiter = rate_limiter
    app.state.user_store = pg_user_store

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(research.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")

    return app
