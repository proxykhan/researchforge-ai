"""Repository protocol for research job persistence.

Any class that implements these methods — whether backed by a dict, SQLite,
or PostgreSQL — is a valid repository.  The service layer depends on this
protocol, never on a concrete implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from researchforge.agents.state import EvaluationResult
from researchforge.integrations.models import PaperResult


@dataclass
class ResearchJobRecord:
    """Storage-agnostic representation of a research job.

    This sits between the service layer and the repository — the service
    reads/writes these, and the repository maps them to its storage backend.
    """

    id: str
    question: str
    status: str
    created_at: datetime
    user_id: str = ""
    completed_at: datetime | None = None
    search_queries: list[str] = field(default_factory=list)
    papers: list[PaperResult] = field(default_factory=list)
    synthesis: str | None = None
    error: str | None = None
    evaluation: EvaluationResult | None = None


class ResearchRepository(Protocol):
    """Contract for research job storage."""

    async def save(self, record: ResearchJobRecord) -> None:
        """Persist a new or updated job record."""
        ...

    async def get(self, job_id: str) -> ResearchJobRecord | None:
        """Retrieve a job by ID, or None if not found."""
        ...

    async def list_all(self, *, user_id: str | None = None) -> list[ResearchJobRecord]:
        """List jobs newest-first, optionally filtered by user."""
        ...
