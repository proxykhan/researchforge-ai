"""Tests for the ResearchService."""

from __future__ import annotations

import asyncio

from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import Author, PaperResult
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message
from researchforge.services.research import ResearchService

from .conftest import FakeLLM, FakeSearchProvider

SAMPLE_PAPER = PaperResult(
    source="test",
    source_id="999",
    title="Service Test Paper",
    authors=[Author(name="Bob")],
    abstract="Testing the service layer.",
    url="https://example.com",
)


def _make_service(
    llm_responses: list[str] | None = None,
    papers: list[PaperResult] | None = None,
) -> ResearchService:
    responses = llm_responses or [
        '["test query"]',
        "Research synthesis result.",
    ]
    llm = FakeLLM(responses=responses)
    provider = FakeSearchProvider("fake", papers or [SAMPLE_PAPER])
    registry = ProviderRegistry(providers=[])
    registry.register(provider)  # type: ignore[arg-type]
    return ResearchService(llm=llm, registry=registry)


class TestCreateJob:
    async def test_returns_summary_with_queued_status(self):
        service = _make_service()
        summary = service.create_job("What is RAG?")
        assert summary.question == "What is RAG?"
        assert summary.status == ResearchStatus.QUEUED
        assert summary.id

    async def test_job_is_retrievable(self):
        service = _make_service()
        summary = service.create_job("What is RAG?")
        detail = service.get_job(summary.id)
        assert detail is not None
        assert detail.id == summary.id


class TestGetJob:
    def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert service.get_job("nonexistent") is None

    async def test_completed_job_has_results(self):
        service = _make_service()
        summary = service.create_job("What is RAG?")

        await asyncio.sleep(0.3)

        detail = service.get_job(summary.id)
        assert detail is not None
        assert detail.status == ResearchStatus.COMPLETED
        assert detail.synthesis is not None
        assert detail.paper_count > 0
        assert detail.completed_at is not None


class TestGetStatus:
    def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert service.get_status("nonexistent") is None

    async def test_returns_status_for_known_job(self):
        service = _make_service()
        summary = service.create_job("test question")
        status = service.get_status(summary.id)
        assert status is not None
        assert status.id == summary.id


class TestGetSources:
    def test_returns_none_for_unknown_id(self):
        service = _make_service()
        assert service.get_sources("nonexistent") is None

    async def test_returns_papers_after_completion(self):
        service = _make_service()
        summary = service.create_job("What is RAG?")

        await asyncio.sleep(0.3)

        sources = service.get_sources(summary.id)
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
        service = ResearchService(llm=ExplodingLLM(), registry=registry)

        summary = service.create_job("Will this fail?")
        await asyncio.sleep(0.3)

        detail = service.get_job(summary.id)
        assert detail is not None
        assert detail.status == ResearchStatus.FAILED
        assert detail.error is not None
