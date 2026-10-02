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

OWNER = "user-1"
OTHER_USER = "user-2"

SAMPLE_PAPER = PaperResult(
    source="test",
    source_id="999",
    title="Service Test Paper",
    authors=[Author(name="Bob")],
    abstract="Testing the service layer.",
    url="https://example.com",
)


def _default_llm_responses() -> list[str]:
    """Build the LLM responses for a full graph run, in call order."""
    return [
        json.dumps(
            {
                "domain": "test",
                "subtasks": ["sub"],
                "search_queries": ["test query"],
                "completion_criteria": "done",
            }
        ),
        json.dumps({"relevant": [1]}),
        "Research synthesis result.",
        json.dumps([{"claim": "test", "status": "supported", "confidence": 0.9}]),
        json.dumps(
            {
                "support_argument": "Support argument.",
                "skeptic_argument": "Skeptic argument.",
                "judgment": "balanced",
                "conclusion": "conclusion",
            }
        ),
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
        summary = await service.create_job(user_id=OWNER, question="What is RAG?")
        assert summary.question == "What is RAG?"
        assert summary.status == ResearchStatus.QUEUED
        assert summary.id

    async def test_job_is_retrievable(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="What is RAG?")
        detail = await service.get_job(summary.id, user_id=OWNER)
        assert detail is not None
        assert detail.id == summary.id


class TestGetJob:
    async def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert await service.get_job("nonexistent", user_id=OWNER) is None

    async def test_completed_job_has_results(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="What is RAG?")

        await asyncio.sleep(0.3)

        detail = await service.get_job(summary.id, user_id=OWNER)
        assert detail is not None
        assert detail.status == ResearchStatus.COMPLETED
        assert detail.synthesis is not None
        assert detail.paper_count > 0
        assert detail.completed_at is not None


class TestGetStatus:
    async def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert await service.get_status("nonexistent", user_id=OWNER) is None

    async def test_returns_status_for_known_job(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="test question")
        status = await service.get_status(summary.id, user_id=OWNER)
        assert status is not None
        assert status.id == summary.id


class TestGetSources:
    async def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert await service.get_sources("nonexistent", user_id=OWNER) is None

    async def test_returns_papers_after_completion(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="What is RAG?")

        await asyncio.sleep(0.3)

        sources = await service.get_sources(summary.id, user_id=OWNER)
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

        summary = await service.create_job(user_id=OWNER, question="Will this fail?")
        await asyncio.sleep(0.3)

        detail = await service.get_job(summary.id, user_id=OWNER)
        assert detail is not None
        assert detail.status == ResearchStatus.FAILED
        assert detail.error is not None


class TestListJobs:
    async def test_empty_list(self):
        service = _make_service()
        assert await service.list_jobs(user_id=OWNER) == []

    async def test_lists_created_jobs(self):
        service = _make_service()
        await service.create_job(user_id=OWNER, question="Question one")
        await service.create_job(user_id=OWNER, question="Question two")

        jobs = await service.list_jobs(user_id=OWNER)
        assert len(jobs) == 2
        assert jobs[0].question == "Question two"
        assert jobs[1].question == "Question one"


class TestCancelJob:
    async def test_cancel_running_job(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="Cancel me")

        cancelled = await service.cancel_job(summary.id, user_id=OWNER)
        assert cancelled

        detail = await service.get_job(summary.id, user_id=OWNER)
        assert detail is not None
        assert detail.status == ResearchStatus.FAILED
        assert detail.error == "Cancelled by user"

    async def test_cancel_nonexistent(self):
        service = _make_service()
        assert await service.cancel_job("nope", user_id=OWNER) is False


class TestGetReport:
    async def test_report_returns_none_for_unknown(self):
        service = _make_service()
        assert await service.get_report("nope", user_id=OWNER) is None

    async def test_report_returns_detail_after_completion(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="What is RAG?")

        await asyncio.sleep(0.3)

        report = await service.get_report(summary.id, user_id=OWNER)
        assert report is not None
        assert report.synthesis is not None
        assert report.status == ResearchStatus.COMPLETED


class TestOwnership:
    async def test_list_only_returns_own_jobs(self):
        service = _make_service()
        await service.create_job(user_id=OWNER, question="Mine")
        await service.create_job(user_id=OTHER_USER, question="Theirs")

        jobs = await service.list_jobs(user_id=OWNER)

        assert [j.question for j in jobs] == ["Mine"]

    async def test_other_users_job_is_reported_missing(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="Private question")
        await asyncio.sleep(0.3)

        assert await service.get_job(summary.id, user_id=OTHER_USER) is None
        assert await service.get_status(summary.id, user_id=OTHER_USER) is None
        assert await service.get_sources(summary.id, user_id=OTHER_USER) is None
        assert await service.get_report(summary.id, user_id=OTHER_USER) is None

    async def test_cannot_cancel_other_users_job(self):
        service = _make_service()
        summary = await service.create_job(user_id=OWNER, question="Keep running")

        assert await service.cancel_job(summary.id, user_id=OTHER_USER) is False
        status = await service.get_status(summary.id, user_id=OWNER)
        assert status is not None
        assert status.status != ResearchStatus.FAILED
