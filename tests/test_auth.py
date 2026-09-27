"""Tests for API key authentication."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from researchforge.api.app import create_app
from researchforge.auth.api_key import generate_api_key, hash_api_key
from researchforge.auth.dependencies import AuthenticatedUser
from researchforge.auth.user_store import InMemoryUserStore
from researchforge.config import Settings
from researchforge.integrations.models import Author, PaperResult
from researchforge.integrations.registry import ProviderRegistry
from researchforge.repositories.memory import InMemoryResearchRepository
from researchforge.workers.manager import JobManager

from .conftest import FakeLLM, FakeSearchProvider

SAMPLE_PAPER = PaperResult(
    source="test",
    source_id="123",
    title="Test Paper",
    authors=[Author(name="Jane")],
    abstract="Abstract.",
    url="https://example.com",
)


class TestApiKeyUtils:
    def test_generate_returns_nonempty_string(self):
        key = generate_api_key()
        assert isinstance(key, str)
        assert len(key) > 20

    def test_different_keys_each_call(self):
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert k1 != k2

    def test_hash_is_deterministic(self):
        key = "test-key-123"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2
        assert len(h1) == 64

    def test_different_keys_different_hashes(self):
        h1 = hash_api_key("key-one")
        h2 = hash_api_key("key-two")
        assert h1 != h2


class TestInMemoryUserStore:
    async def test_find_existing_user(self):
        store = InMemoryUserStore()
        user = AuthenticatedUser(id="u1", email="a@b.com", name="Alice")
        store.add_user("hash123", user)

        result = await store.find_by_key_hash("hash123")
        assert result is not None
        assert result.id == "u1"

    async def test_find_missing_returns_none(self):
        store = InMemoryUserStore()
        assert await store.find_by_key_hash("nope") is None


def _llm_responses() -> list[str]:
    return [
        json.dumps(
            {
                "domain": "AI",
                "subtasks": ["sub"],
                "search_queries": ["query"],
                "completion_criteria": "done",
            }
        ),
        "Synthesis.",
        json.dumps([{"claim": "c", "status": "supported", "confidence": 0.9}]),
        "Support.",
        "Skeptic.",
        json.dumps({"judgment": "balanced", "conclusion": "ok"}),
        json.dumps({"completeness_score": 0.9, "needs_more_research": False, "feedback": "ok"}),
        json.dumps(
            {
                "retrieval_score": 0.8,
                "citation_score": 0.7,
                "factual_grounding_score": 0.8,
                "relevance_score": 0.9,
                "completeness_score": 0.8,
                "overall_score": 0.8,
                "strengths": ["Good"],
                "weaknesses": [],
                "summary": "Solid.",
            }
        ),
    ]


def _make_authed_client() -> tuple[TestClient, str]:
    """Create a test client with auth ENABLED and return (client, api_key)."""
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    store = InMemoryUserStore()
    store.add_user(key_hash, AuthenticatedUser(id="u1", email="a@b.com", name="Alice"))

    llm = FakeLLM(responses=_llm_responses())
    provider = FakeSearchProvider("test", [SAMPLE_PAPER])
    registry = ProviderRegistry(providers=[])
    registry.register(provider)  # type: ignore[arg-type]
    manager = JobManager()
    manager.start()
    repo = InMemoryResearchRepository()
    settings = Settings(auth_enabled=True)
    app = create_app(
        settings=settings,
        llm=llm,
        registry=registry,
        job_manager=manager,
        repository=repo,
        user_lookup=store,
    )
    return TestClient(app), api_key


class TestAuthEndpoints:
    def test_no_key_returns_401(self):
        client, _ = _make_authed_client()
        resp = client.post("/api/v1/research", json={"question": "What is AI?"})
        assert resp.status_code == 401

    def test_invalid_key_returns_401(self):
        client, _ = _make_authed_client()
        resp = client.post(
            "/api/v1/research",
            json={"question": "What is AI?"},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401

    def test_valid_key_returns_201(self):
        client, key = _make_authed_client()
        resp = client.post(
            "/api/v1/research",
            json={"question": "What is AI?"},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert resp.status_code == 201

    def test_list_with_valid_key(self):
        client, key = _make_authed_client()
        resp = client.get(
            "/api/v1/research",
            headers={"Authorization": f"Bearer {key}"},
        )
        assert resp.status_code == 200

    def test_health_does_not_require_auth(self):
        client, _ = _make_authed_client()
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
