"""Tests for health and readiness endpoints."""

from fastapi.testclient import TestClient

from researchforge import __version__
from researchforge.api.app import create_app
from researchforge.integrations.registry import ProviderRegistry

from .conftest import FakeLLM


def _make_client() -> TestClient:
    app = create_app(
        llm=FakeLLM(responses=[]),
        registry=ProviderRegistry(providers=[]),
    )
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        client = _make_client()
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == __version__

    def test_ready_returns_ok(self):
        client = _make_client()
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
