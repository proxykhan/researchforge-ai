"""In-memory repository for testing and development.

Stores records in a plain dict — fast, no I/O, no database needed.
"""

from __future__ import annotations

from researchforge.repositories.base import ResearchJobRecord


class InMemoryResearchRepository:
    """Dict-backed implementation of the ResearchRepository protocol."""

    def __init__(self) -> None:
        self._records: dict[str, ResearchJobRecord] = {}

    async def save(self, record: ResearchJobRecord) -> None:
        self._records[record.id] = record

    async def get(self, job_id: str) -> ResearchJobRecord | None:
        return self._records.get(job_id)

    async def list_all(self, *, user_id: str | None = None) -> list[ResearchJobRecord]:
        records = list(self._records.values())
        if user_id is not None:
            records = [r for r in records if r.user_id == user_id]
        return sorted(records, key=lambda r: r.created_at, reverse=True)
