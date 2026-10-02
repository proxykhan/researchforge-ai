"""Research service — business logic for managing research jobs.

This layer owns job lifecycle, status transitions, and background execution.
The API layer delegates here; the agent layer runs underneath.
Storage is delegated to a ResearchRepository (in-memory for tests,
PostgreSQL for production).
"""

from __future__ import annotations

import logging
import uuid
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
from researchforge.repositories.base import ResearchJobRecord, ResearchRepository
from researchforge.workers.manager import JobManager

logger = logging.getLogger(__name__)


class ResearchService:
    """Manages research job lifecycle.

    Storage is delegated to a ResearchRepository implementation —
    InMemoryResearchRepository for tests, PostgresResearchRepository
    for production.
    """

    def __init__(
        self,
        llm: LLMProvider,
        registry: ProviderRegistry,
        repository: ResearchRepository,
        llm_config: LLMConfig | None = None,
        job_manager: JobManager | None = None,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._repo = repository
        self._llm_config = llm_config or LLMConfig()
        self._job_manager = job_manager or JobManager()

    @property
    def job_manager(self) -> JobManager:
        return self._job_manager

    async def create_job(self, question: str, *, user_id: str = "") -> ResearchSummary:
        """Create a new research job and schedule it for background execution."""
        job_id = str(uuid.uuid4())
        record = ResearchJobRecord(
            id=job_id,
            question=question,
            status=ResearchStatus.QUEUED,
            created_at=datetime.now(UTC),
            user_id=user_id,
        )
        await self._repo.save(record)
        self._job_manager.submit(job_id, lambda: self._run_research(job_id))
        return _to_summary(record)

    async def list_jobs(self, *, user_id: str) -> list[ResearchSummary]:
        """List the user's research jobs, newest first."""
        records = await self._repo.list_all(user_id=user_id)
        return [_to_summary(r) for r in records]

    async def _get_owned(self, job_id: str, user_id: str) -> ResearchJobRecord | None:
        """Return the job only if it belongs to ``user_id``.

        Another user's job is reported as missing so job IDs cannot be probed.
        """
        record = await self._repo.get(job_id)
        if record is None or record.user_id != user_id:
            return None
        return record

    async def get_job(self, job_id: str, *, user_id: str) -> ResearchDetail | None:
        """Get full details for a research job."""
        record = await self._get_owned(job_id, user_id)
        if record is None:
            return None
        return _to_detail(record)

    async def get_status(self, job_id: str, *, user_id: str) -> StatusResponse | None:
        """Lightweight status check."""
        record = await self._get_owned(job_id, user_id)
        if record is None:
            return None
        return StatusResponse(id=record.id, status=ResearchStatus(record.status))

    async def get_sources(self, job_id: str, *, user_id: str) -> ResearchSourcesResponse | None:
        """Get the papers found during research."""
        record = await self._get_owned(job_id, user_id)
        if record is None:
            return None
        return ResearchSourcesResponse(
            id=record.id,
            papers=[_paper_to_response(p) for p in record.papers],
        )

    async def get_report(self, job_id: str, *, user_id: str) -> ResearchDetail | None:
        """Get the final report including evaluation data."""
        record = await self._get_owned(job_id, user_id)
        if record is None:
            return None
        return _to_detail(record)

    async def cancel_job(self, job_id: str, *, user_id: str) -> bool:
        """Cancel a research job. Returns True if cancellation was requested."""
        record = await self._get_owned(job_id, user_id)
        if record is None:
            return False
        cancelled = self._job_manager.cancel(job_id)
        if cancelled:
            record.status = ResearchStatus.FAILED
            record.error = "Cancelled by user"
            record.completed_at = datetime.now(UTC)
            await self._repo.save(record)
        return cancelled

    async def _run_research(self, job_id: str) -> None:
        """Execute the research graph in the background."""
        record = await self._repo.get(job_id)
        if record is None:
            return
        try:
            graph = build_research_graph(self._llm, self._registry, self._llm_config)
            compiled = graph.compile()

            async def _update_status(status: ResearchStatus) -> None:
                record.status = status
                await self._repo.save(record)

            result: ResearchState = await compiled.ainvoke(  # type: ignore[assignment]
                {"question": record.question, "status_callback": _update_status}
            )

            record.search_queries = result.get("search_queries", [])
            record.papers = result.get("papers", [])
            record.synthesis = result.get("synthesis")
            record.error = result.get("error")
            record.evaluation = result.get("evaluation")
            record.status = ResearchStatus.COMPLETED
            record.completed_at = datetime.now(UTC)
            await self._repo.save(record)
            logger.info(
                "Research job %s completed with %d papers",
                job_id,
                len(record.papers),
            )

        except Exception as exc:
            record.status = ResearchStatus.FAILED
            record.error = f"Research failed: {exc}"
            record.completed_at = datetime.now(UTC)
            await self._repo.save(record)
            logger.exception("Research job %s failed", job_id)


def _to_summary(record: ResearchJobRecord) -> ResearchSummary:
    return ResearchSummary(
        id=record.id,
        question=record.question,
        status=ResearchStatus(record.status),
        created_at=record.created_at,
    )


def _to_detail(record: ResearchJobRecord) -> ResearchDetail:
    return ResearchDetail(
        id=record.id,
        question=record.question,
        status=ResearchStatus(record.status),
        created_at=record.created_at,
        completed_at=record.completed_at,
        search_queries=record.search_queries,
        paper_count=len(record.papers),
        synthesis=record.synthesis,
        error=record.error,
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
