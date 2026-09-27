"""Tests for the ResearchService."""

from __future__ import annotations

import asyncio
import json

from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import Author, PaperResult
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message
from researchforge.repositories.memory import InMemoryResearchRepository
from researchforge.services.research import ResearchService
from researchforge.workers.manager import JobManager

from .conftest import FakeLLM, FakeSearchProvider

SAMPLE_PAPER = PaperResult(
    source="test",
    source_id="999",
    title="Service Test Paper",
    authors=[Author(name="Bob")],
    abstract="Testing the service layer.",
    url="https://example.com",
)


def _default_llm_responses() -> list[str]:
    """Build the 8 LLM responses needed for a full graph run."""
    return [
        json.dumps(
            {
                "domain": "test",
                "subtasks": ["sub"],
                "search_queries": ["test query"],
                "completion_criteria": "done",
            }
        ),
        "Research synthesis result.",
        json.dumps([{"claim": "test", "status": "supported", "confidence": 0.9}]),
        "Support argument.",
        "Skeptic argument.",
        json.dumps({"judgment": "balanced", "conclusion": "conclusion"}),
        json.dumps(
            {
                "completeness_score": 0.85,
                "needs_more_research": False,
                "feedback": "ok",
            }
        ),
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


def _make_service(
    llm_responses: list[str] | None = None,
    papers: list[PaperResult] | None = None,
) -> ResearchService:
    responses = llm_responses or _default_llm_responses()
    llm = FakeLLM(responses=responses)
    provider = FakeSearchProvider("fake", papers or [SAMPLE_PAPER])
    registry = ProviderRegistry(providers=[])
    registry.register(provider)  # type: ignore[arg-type]
    manager = JobManager()
    manager.start()
    repo = InMemoryResearchRepository()
    return ResearchService(llm=llm, registry=registry, repository=repo, job_manager=manager)


class TestCreateJob:
    async def test_returns_summary_with_queued_status(self):
        service = _make_service()
        summary = await service.create_job("What is RAG?")
        assert summary.question == "What is RAG?"
        assert summary.status == ResearchStatus.QUEUED
        assert summary.id

    async def test_job_is_retrievable(self):
        service = _make_service()
        summary = await service.create_job("What is RAG?")
        detail = await service.get_job(summary.id)
        assert detail is not None
        assert detail.id == summary.id


class TestGetJob:
    async def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert await service.get_job("nonexistent") is None

    async def test_completed_job_has_results(self):
        service = _make_service()
        summary = await service.create_job("What is RAG?")

        await asyncio.sleep(0.3)

        detail = await service.get_job(summary.id)
        assert detail is not None
        assert detail.status == ResearchStatus.COMPLETED
        assert detail.synthesis is not None
        assert detail.paper_count > 0
        assert detail.completed_at is not None


class TestGetStatus:
    async def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert await service.get_status("nonexistent") is None

    async def test_returns_status_for_known_job(self):
        service = _make_service()
        summary = await service.create_job("test question")
        status = await service.get_status(summary.id)
        assert status is not None
        assert status.id == summary.id


class TestGetSources:
    async def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert await service.get_sources("nonexistent") is None

    async def test_returns_papers_after_completion(self):
        service = _make_service()
        summary = await service.create_job("What is RAG?")

        await asyncio.sleep(0.3)

        sources = await service.get_sources(summary.id)
        assert sources is not None
        assert len(sources.papers) > 0
        assert sources.papers[0].title == "Service Test Paper"


class TestFailedJob:
    async def test_failed_job_has_error(self):

        class ExplodingLLM(LLMProvider):
            @property
            def name(self) -> str:
                return "exploding"

            async def complete(
                self, messages: list[Message], config: LLMConfig | None = None
            ) -> LLMResponse:
                raise RuntimeError("LLM exploded")

        registry = ProviderRegistry(providers=[])
        manager = JobManager()
        manager.start()
        repo = InMemoryResearchRepository()
        service = ResearchService(
            llm=ExplodingLLM(), registry=registry, repository=repo, job_manager=manager
        )

        summary = await service.create_job("Will this fail?")
        await asyncio.sleep(0.3)

        detail = await service.get_job(summary.id)
        assert detail is not None
        assert detail.status == ResearchStatus.FAILED
        assert detail.error is not None


class TestListJobs:
    async def test_empty_list(self):
        service = _make_service()
        assert await service.list_jobs() == []

    async def test_lists_created_jobs(self):
        service = _make_service()
        await service.create_job("Question one")
        await service.create_job("Question two")

        jobs = await service.list_jobs()
        assert len(jobs) == 2
        assert jobs[0].question == "Question two"
        assert jobs[1].question == "Question one"


class TestCancelJob:
    async def test_cancel_running_job(self):
        service = _make_service()
        summary = await service.create_job("Cancel me")

        cancelled = await service.cancel_job(summary.id)
        assert cancelled

        detail = await service.get_job(summary.id)
        assert detail is not None
        assert detail.status == ResearchStatus.FAILED
        assert detail.error == "Cancelled by user"

    async def test_cancel_nonexistent(self):
        service = _make_service()
        assert await service.cancel_job("nope") is False


class TestGetReport:
    async def test_report_returns_none_for_unknown(self):
        service = _make_service()
        assert await service.get_report("nope") is None

    async def test_report_returns_detail_after_completion(self):
        service = _make_service()
        summary = await service.create_job("What is RAG?")

        await asyncio.sleep(0.3)

        report = await service.get_report(summary.id)
        assert report is not None
        assert report.synthesis is not None
        assert report.status == ResearchStatus.COMPLETED
