"""Tests for the repository layer."""

from __future__ import annotations

from datetime import UTC, datetime

from researchforge.integrations.models import Author, PaperResult
from researchforge.repositories.base import ResearchJobRecord
from researchforge.repositories.memory import InMemoryResearchRepository


def _make_record(
    job_id: str = "j1",
    question: str = "What is AI?",
    status: str = "queued",
    user_id: str = "u1",
) -> ResearchJobRecord:
    return ResearchJobRecord(
        id=job_id,
        question=question,
        status=status,
        created_at=datetime.now(UTC),
        user_id=user_id,
    )


class TestInMemoryRepository:
    async def test_save_and_get(self):
        repo = InMemoryResearchRepository()
        record = _make_record()
        await repo.save(record)

        result = await repo.get("j1")
        assert result is not None
        assert result.id == "j1"
        assert result.question == "What is AI?"

    async def test_get_returns_none_for_missing(self):
        repo = InMemoryResearchRepository()
        assert await repo.get("nonexistent") is None

    async def test_save_updates_existing(self):
        repo = InMemoryResearchRepository()
        record = _make_record()
        await repo.save(record)

        record.status = "completed"
        record.synthesis = "AI is amazing."
        await repo.save(record)

        result = await repo.get("j1")
        assert result is not None
        assert result.status == "completed"
        assert result.synthesis == "AI is amazing."

    async def test_list_all_returns_newest_first(self):
        repo = InMemoryResearchRepository()
        r1 = _make_record(job_id="j1", question="First")
        r2 = _make_record(job_id="j2", question="Second")
        await repo.save(r1)
        await repo.save(r2)

        results = await repo.list_all()
        assert len(results) == 2
        assert results[0].id == "j2"
        assert results[1].id == "j1"

    async def test_list_all_empty(self):
        repo = InMemoryResearchRepository()
        assert await repo.list_all() == []

    async def test_list_all_filters_by_user_id(self):
        repo = InMemoryResearchRepository()
        await repo.save(_make_record(job_id="j1", user_id="alice"))
        await repo.save(_make_record(job_id="j2", user_id="bob"))
        await repo.save(_make_record(job_id="j3", user_id="alice"))

        results = await repo.list_all(user_id="alice")
        assert len(results) == 2
        assert all(r.user_id == "alice" for r in results)

    async def test_record_with_papers(self):
        repo = InMemoryResearchRepository()
        record = _make_record()
        record.papers = [
            PaperResult(
                source="arxiv",
                source_id="123",
                title="Test Paper",
                authors=[Author(name="Jane")],
                abstract="Abstract.",
                url="https://example.com",
            )
        ]
        await repo.save(record)

        result = await repo.get("j1")
        assert result is not None
        assert len(result.papers) == 1
        assert result.papers[0].title == "Test Paper"
