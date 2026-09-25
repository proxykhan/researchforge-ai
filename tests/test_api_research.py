"""Tests for research API endpoints."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from researchforge.api.app import create_app
from researchforge.integrations.models import Author, PaperResult
from researchforge.integrations.registry import ProviderRegistry

from .conftest import FakeLLM, FakeSearchProvider

SAMPLE_PAPER = PaperResult(
    source="test",
    source_id="123",
    title="Test Paper on AI",
    authors=[Author(name="Jane Doe")],
    abstract="An abstract about AI.",
    url="https://example.com/paper",
    citation_count=10,
)


def _make_client(
    llm_responses: list[str] | None = None,
    papers: list[PaperResult] | None = None,
) -> TestClient:
    responses = llm_responses or [
        '["AI research query"]',
        "Summary of research findings on AI.",
    ]
    llm = FakeLLM(responses=responses)
    provider = FakeSearchProvider("test_prov", papers or [SAMPLE_PAPER])
    registry = ProviderRegistry(providers=[])
    registry.register(provider)  # type: ignore[arg-type]
    app = create_app(llm=llm, registry=registry)
    return TestClient(app)


class TestCreateResearch:
    def test_returns_201_with_job_id(self):
        client = _make_client()
        resp = client.post("/api/v1/research", json={"question": "What is deep learning?"})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["question"] == "What is deep learning?"
        assert data["status"] == "queued"

    def test_rejects_empty_question(self):
        client = _make_client()
        resp = client.post("/api/v1/research", json={"question": ""})
        assert resp.status_code == 422

    def test_rejects_missing_question(self):
        client = _make_client()
        resp = client.post("/api/v1/research", json={})
        assert resp.status_code == 422

    def test_rejects_too_short_question(self):
        client = _make_client()
        resp = client.post("/api/v1/research", json={"question": "ab"})
        assert resp.status_code == 422


class TestGetResearch:
    def test_returns_job_details(self):
        client = _make_client()
        create_resp = client.post("/api/v1/research", json={"question": "What is deep learning?"})
        job_id = create_resp.json()["id"]

        time.sleep(0.3)

        resp = client.get(f"/api/v1/research/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["question"] == "What is deep learning?"
        assert data["status"] in ("queued", "planning", "completed")

    def test_404_for_unknown_id(self):
        client = _make_client()
        resp = client.get("/api/v1/research/nonexistent-id")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestGetResearchStatus:
    def test_returns_status(self):
        client = _make_client()
        create_resp = client.post("/api/v1/research", json={"question": "What is deep learning?"})
        job_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/research/{job_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert "status" in data

    def test_404_for_unknown_id(self):
        client = _make_client()
        resp = client.get("/api/v1/research/nonexistent-id/status")
        assert resp.status_code == 404


class TestGetResearchSources:
    def test_returns_papers_after_completion(self):
        client = _make_client()
        create_resp = client.post("/api/v1/research", json={"question": "What is deep learning?"})
        job_id = create_resp.json()["id"]

        time.sleep(0.3)

        resp = client.get(f"/api/v1/research/{job_id}/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert isinstance(data["papers"], list)

    def test_404_for_unknown_id(self):
        client = _make_client()
        resp = client.get("/api/v1/research/nonexistent-id/sources")
        assert resp.status_code == 404
