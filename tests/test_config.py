"""Tests for application configuration."""

from researchforge.config import Settings, load_settings


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
