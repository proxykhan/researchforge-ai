"""Research service — business logic for managing research jobs.

This layer owns job lifecycle, status transitions, and background execution.
The API layer delegates here; the agent layer runs underneath.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from researchforge.agents.research import ResearchState, build_research_graph
from researchforge.api.schemas import (
    PaperResponse,
    ResearchDetail,
    ResearchSourcesResponse,
    ResearchStatus,
    ResearchSummary,
    StatusResponse,
)
from researchforge.integrations.models import PaperResult
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class ResearchJob:
    """In-memory representation of a research job."""

    id: str
    question: str
    status: ResearchStatus
    created_at: datetime
    completed_at: datetime | None = None
    search_queries: list[str] = field(default_factory=list)
    papers: list[PaperResult] = field(default_factory=list)
    synthesis: str | None = None
    error: str | None = None


class ResearchService:
    """Manages research job lifecycle.

    Uses an in-memory dict for storage — replaced by a database repository
    in Phase 9.
    """

    def __init__(
        self,
        llm: LLMProvider,
        registry: ProviderRegistry,
        llm_config: LLMConfig | None = None,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._llm_config = llm_config or LLMConfig()
        self._jobs: dict[str, ResearchJob] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def create_job(self, question: str) -> ResearchSummary:
        """Create a new research job and schedule it for background execution."""
        job_id = str(uuid.uuid4())
        job = ResearchJob(
            id=job_id,
            question=question,
            status=ResearchStatus.QUEUED,
            created_at=datetime.now(UTC),
        )
        self._jobs[job_id] = job
        task = asyncio.create_task(self._run_research(job_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return self._to_summary(job)

    def get_job(self, job_id: str) -> ResearchDetail | None:
        """Get full details for a research job."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return ResearchDetail(
            id=job.id,
            question=job.question,
            status=job.status,
            created_at=job.created_at,
            completed_at=job.completed_at,
            search_queries=job.search_queries,
            paper_count=len(job.papers),
            synthesis=job.synthesis,
            error=job.error,
        )

    def get_status(self, job_id: str) -> StatusResponse | None:
        """Lightweight status check."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return StatusResponse(id=job.id, status=job.status)

    def get_sources(self, job_id: str) -> ResearchSourcesResponse | None:
        """Get the papers found during research."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return ResearchSourcesResponse(
            id=job.id,
            papers=[_paper_to_response(p) for p in job.papers],
        )

    async def _run_research(self, job_id: str) -> None:
        """Execute the research graph in the background."""
        job = self._jobs[job_id]
        try:
            graph = build_research_graph(self._llm, self._registry, self._llm_config)
            compiled = graph.compile()

            def _update_status(status: ResearchStatus) -> None:
                job.status = status

            result: ResearchState = await compiled.ainvoke(  # type: ignore[assignment]
                {"question": job.question, "status_callback": _update_status}
            )

            job.search_queries = result.get("search_queries", [])
            job.papers = result.get("papers", [])
            job.synthesis = result.get("synthesis")
            job.error = result.get("error")

            job.status = ResearchStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            logger.info("Research job %s completed with %d papers", job_id, len(job.papers))

        except Exception:
            job.status = ResearchStatus.FAILED
            job.error = "Research failed unexpectedly"
            job.completed_at = datetime.now(UTC)
            logger.exception("Research job %s failed", job_id)

    @staticmethod
    def _to_summary(job: ResearchJob) -> ResearchSummary:
        return ResearchSummary(
            id=job.id,
            question=job.question,
            status=job.status,
            created_at=job.created_at,
        )


def _paper_to_response(paper: PaperResult) -> PaperResponse:
    return PaperResponse(
        source=paper.source,
        source_id=paper.source_id,
        title=paper.title,
        authors=[a.name for a in paper.authors],
        abstract=paper.abstract,
        url=paper.url,
        published_date=str(paper.published_date) if paper.published_date else None,
        doi=paper.doi,
        citation_count=paper.citation_count,
    )
