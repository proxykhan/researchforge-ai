"""Tests for application configuration."""

from sqlalchemy.ext.asyncio import create_async_engine

from researchforge.config import Settings, load_settings, normalize_database_url

NEON_URL = (
    "postgresql://user:p%40ss@ep-cool-name-123.us-west-2.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


class TestNormalizeDatabaseUrl:
    def test_render_internal_url_gets_asyncpg_scheme(self):
        assert normalize_database_url("postgres://u:p@dpg-abc/researchforge") == (
            "postgresql+asyncpg://u:p@dpg-abc/researchforge"
        )

    def test_neon_url_is_translated_for_asyncpg(self):
        assert normalize_database_url(NEON_URL) == (
            "postgresql+asyncpg://user:p%40ss@ep-cool-name-123.us-west-2.aws.neon.tech/neondb"
            "?ssl=require"
        )

    def test_asyncpg_receives_only_arguments_it_accepts(self):
        engine = create_async_engine(normalize_database_url(NEON_URL))
        _, kwargs = engine.dialect.create_connect_args(engine.url)
        assert kwargs["ssl"] == "require"
        assert "sslmode" not in kwargs
        assert "channel_binding" not in kwargs
        assert kwargs["password"] == "p@ss"

    def test_drops_query_entirely_when_nothing_left(self):
        assert normalize_database_url("postgresql://u:p@h/db?channel_binding=require") == (
            "postgresql+asyncpg://u:p@h/db"
        )

    def test_empty_and_already_normalized(self):
        assert normalize_database_url("") == ""
        url = "postgresql+asyncpg://u:p@h/db?ssl=require"
        assert normalize_database_url(url) == url


class TestSettings:
    def test_default_settings(self):
        settings = Settings()
        assert settings.app_env == "development"
        assert settings.app_name == "researchforge-ai"
        assert settings.log_level == "INFO"
        assert settings.llm_provider == "anthropic"
        assert settings.is_production is False
        assert settings.is_testing is False

    def test_production_detection(self):
        settings = Settings(app_env="production")
        assert settings.is_production is True
        assert settings.is_testing is False

    def test_testing_detection(self):
        settings = Settings(app_env="testing")
        assert settings.is_testing is True
        assert settings.is_production is False

    def test_settings_immutable(self):
        settings = Settings()
        try:
            settings.app_env = "production"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


class TestLoadSettings:
    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        settings = load_settings()
        assert settings.app_env == "testing"
        assert settings.app_name == "test-app"
        assert settings.llm_provider == "openai"

    def test_load_defaults(self, monkeypatch):
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("APP_NAME", raising=False)

        settings = load_settings()
        assert settings.app_env == "development"
        assert settings.app_name == "researchforge-ai"
