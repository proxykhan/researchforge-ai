"""Tests for research API endpoints."""

from __future__ import annotations

import json
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
        json.dumps(
            {
                "domain": "AI",
                "subtasks": ["sub"],
                "search_queries": ["AI research query"],
                "completion_criteria": "done",
            }
        ),
        "Summary of research findings on AI.",
        json.dumps([{"claim": "test", "status": "supported", "confidence": 0.9}]),
        "Support argument.",
        "Skeptic argument.",
        json.dumps({"judgment": "balanced", "conclusion": "conclusion"}),
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
        assert data["status"] in (
            "queued",
            "planning",
            "researching",
            "synthesizing",
            "verifying",
            "debating",
            "critiquing",
            "evaluating",
            "completed",
        )

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
