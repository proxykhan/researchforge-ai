"""Tests for observability: structured logging, middleware, security, tracing."""

from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from researchforge.api.app import create_app
from researchforge.config import Settings
from researchforge.integrations.registry import ProviderRegistry
from researchforge.observability.instrumentation import traced_agent_node
from researchforge.observability.logging import get_logger, setup_logging
from researchforge.observability.middleware import REQUEST_ID_HEADER
from researchforge.observability.security import SECURITY_HEADERS, cors_config

from .conftest import FakeLLM


def _make_client(**overrides: object) -> TestClient:
    defaults = dict(auth_enabled=False)
    defaults.update(overrides)  # type: ignore[arg-type]
    app = create_app(
        settings=Settings(**defaults),  # type: ignore[arg-type]
        llm=FakeLLM(responses=[]),
        registry=ProviderRegistry(providers=[]),
    )
    return TestClient(app)


# ── Structured logging ───────────────────────────────────────────


class TestStructuredLogging:
    def test_setup_logging_json_mode(self, capfd):
        setup_logging(json=True, level="DEBUG")
        logger = logging.getLogger("test.json")
        logger.info("hello")
        out = capfd.readouterr().out
        data = json.loads(out.strip())
        assert data["event"] == "hello"
        assert "timestamp" in data

    def test_setup_logging_console_mode(self, capfd):
        setup_logging(json=False, level="INFO")
        logger = logging.getLogger("test.console")
        logger.info("console check")
        out = capfd.readouterr().out
        assert "console check" in out

    def test_get_logger_returns_bound_logger(self):
        log = get_logger(component="test")
        assert log is not None


# ── Request ID middleware ────────────────────────────────────────


class TestRequestIDMiddleware:
    def test_generates_request_id(self):
        client = _make_client()
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        request_id = resp.headers.get(REQUEST_ID_HEADER)
        assert request_id is not None
        assert len(request_id) == 36  # UUID format

    def test_propagates_incoming_request_id(self):
        client = _make_client()
        custom_id = "custom-trace-12345"
        resp = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: custom_id})
        assert resp.headers[REQUEST_ID_HEADER] == custom_id


# ── Security headers middleware ──────────────────────────────────


class TestSecurityHeaders:
    def test_security_headers_present(self):
        client = _make_client()
        resp = client.get("/api/v1/health")
        for name, value in SECURITY_HEADERS.items():
            assert resp.headers.get(name) == value, f"Missing or wrong header: {name}"

    def test_hsts_absent_in_dev(self):
        client = _make_client(app_env="development")
        resp = client.get("/api/v1/health")
        assert "Strict-Transport-Security" not in resp.headers

    def test_hsts_present_in_production(self):
        client = _make_client(app_env="production")
        resp = client.get("/api/v1/health")
        assert "Strict-Transport-Security" in resp.headers


# ── Request size limit middleware ────────────────────────────────


class TestRequestSizeLimit:
    def test_rejects_oversized_content_length(self):
        client = _make_client()
        resp = client.post(
            "/api/v1/research",
            content=b"x",
            headers={"Content-Length": "999999999", "Content-Type": "application/json"},
        )
        assert resp.status_code == 413

    def test_allows_normal_request(self):
        client = _make_client()
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


# ── CORS configuration ──────────────────────────────────────────


class TestCORSConfig:
    def test_default_no_origins(self):
        cfg = cors_config()
        assert cfg.allow_origins == []

    def test_custom_origins(self):
        cfg = cors_config(allow_origins=["https://example.com"])
        assert cfg.allow_origins == ["https://example.com"]
        assert "X-Request-ID" in cfg.expose_headers

    def test_cors_origin_list_from_settings(self):
        s = Settings(cors_origins="https://a.com, https://b.com")
        assert s.cors_origin_list == ["https://a.com", "https://b.com"]

    def test_cors_origin_list_empty(self):
        s = Settings(cors_origins="")
        assert s.cors_origin_list == []


# ── Agent instrumentation ────────────────────────────────────────


class TestTracedAgentNode:
    async def test_traced_node_passes_through(self):
        async def fake_run(state: dict) -> dict:  # type: ignore[type-arg]
            return {"papers": []}

        wrapped = traced_agent_node("test_agent")(fake_run)
        result = await wrapped({"question": "test"})
        assert result["papers"] == []

    async def test_traced_node_propagates_errors(self):
        async def failing_run(state: dict) -> dict:  # type: ignore[type-arg]
            raise RuntimeError("boom")

        wrapped = traced_agent_node("fail_agent")(failing_run)
        import pytest

        with pytest.raises(RuntimeError, match="boom"):
            await wrapped({"question": "test"})
