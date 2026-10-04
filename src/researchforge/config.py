"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    app_env: str = "development"
    app_name: str = "researchforge-ai"
    log_level: str = "INFO"

    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-5"

    database_url: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 10
    redis_url: str = ""
    auth_enabled: bool = True

    # Observability
    otlp_endpoint: str = ""
    otel_console: bool = False

    # Security
    cors_origins: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def normalize_database_url(url: str) -> str:
    """Adapt a provider's Postgres URL (Render, Neon, ...) for SQLAlchemy + asyncpg.

    asyncpg takes ``ssl`` instead of libpq's ``sslmode`` and has no
    ``channel_binding`` option; passing either crashes the connection at startup.
    """
    if not url:
        return url
    url = re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", url)
    base, _, query = url.partition("?")
    if not query:
        return url
    params = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key == "channel_binding":
            continue
        if key == "sslmode":
            key = "ssl"
        params.append((key, value))
    return f"{base}?{urlencode(params)}" if params else base


def load_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        app_name=os.getenv("APP_NAME", "researchforge-ai"),
        log_level=os.getenv("APP_LOG_LEVEL", "INFO"),
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic"),
        llm_model=os.getenv("LLM_MODEL", "claude-sonnet-5"),
        database_url=normalize_database_url(os.getenv("DATABASE_URL", "")),
        db_pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        redis_url=os.getenv("REDIS_URL", ""),
        auth_enabled=os.getenv("AUTH_ENABLED", "true").lower() == "true",
        otlp_endpoint=os.getenv("OTLP_ENDPOINT", ""),
        otel_console=os.getenv("OTEL_CONSOLE", "false").lower() == "true",
        cors_origins=os.getenv("CORS_ORIGINS", ""),
    )
