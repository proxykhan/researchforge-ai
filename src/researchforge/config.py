"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    app_env: str = "development"
    app_name: str = "researchforge-ai"
    log_level: str = "INFO"

    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-5"

    database_url: str = ""
    redis_url: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


def load_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        app_name=os.getenv("APP_NAME", "researchforge-ai"),
        log_level=os.getenv("APP_LOG_LEVEL", "INFO"),
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic"),
        llm_model=os.getenv("LLM_MODEL", "claude-sonnet-5"),
        database_url=os.getenv("DATABASE_URL", ""),
        redis_url=os.getenv("REDIS_URL", ""),
    )
