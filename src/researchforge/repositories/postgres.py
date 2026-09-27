"""PostgreSQL-backed repository using async SQLAlchemy."""

from __future__ import annotations

import dataclasses
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from researchforge.agents.state import EvaluationResult
from researchforge.database.models import ResearchJobRow
from researchforge.integrations.models import Author, PaperResult
from researchforge.repositories.base import ResearchJobRecord


class PostgresResearchRepository:
    """Persists research jobs in PostgreSQL via SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, record: ResearchJobRecord) -> None:
        async with self._session_factory() as session, session.begin():
            existing = await session.get(ResearchJobRow, record.id)
            if existing is not None:
                existing.status = record.status
                existing.completed_at = record.completed_at
                existing.search_queries = {"items": record.search_queries}
                existing.papers = _papers_to_json(record.papers)
                existing.synthesis = record.synthesis
                existing.error = record.error
                existing.evaluation = _evaluation_to_json(record.evaluation)
                existing.overall_score = (
                    record.evaluation.overall_score if record.evaluation else None
                )
            else:
                row = ResearchJobRow(
                    id=record.id,
                    user_id=record.user_id,
                    question=record.question,
                    status=record.status,
                    created_at=record.created_at,
                    completed_at=record.completed_at,
                    search_queries={"items": record.search_queries},
                    papers=_papers_to_json(record.papers),
                    synthesis=record.synthesis,
                    error=record.error,
                    evaluation=_evaluation_to_json(record.evaluation),
                    overall_score=(record.evaluation.overall_score if record.evaluation else None),
                )
                session.add(row)

    async def get(self, job_id: str) -> ResearchJobRecord | None:
        async with self._session_factory() as session:
            row = await session.get(ResearchJobRow, job_id)
            if row is None:
                return None
            return _row_to_record(row)

    async def list_all(self, *, user_id: str | None = None) -> list[ResearchJobRecord]:
        async with self._session_factory() as session:
            stmt = select(ResearchJobRow).order_by(ResearchJobRow.created_at.desc())
            if user_id is not None:
                stmt = stmt.where(ResearchJobRow.user_id == user_id)
            result = await session.execute(stmt)
            return [_row_to_record(row) for row in result.scalars()]


def _row_to_record(row: ResearchJobRow) -> ResearchJobRecord:
    queries: list[str] = []
    raw_queries = row.search_queries.get("items") if row.search_queries else None
    if isinstance(raw_queries, list):
        queries = raw_queries

    papers: list[PaperResult] = []
    raw_papers = row.papers.get("items") if row.papers else None
    if isinstance(raw_papers, list):
        papers = [_json_to_paper(p) for p in raw_papers]

    evaluation: EvaluationResult | None = None
    if row.evaluation:
        evaluation = _json_to_evaluation(row.evaluation)

    return ResearchJobRecord(
        id=row.id,
        question=row.question,
        status=row.status,
        created_at=row.created_at,
        user_id=row.user_id,
        completed_at=row.completed_at,
        search_queries=queries,
        papers=papers,
        synthesis=row.synthesis,
        error=row.error,
        evaluation=evaluation,
    )


def _papers_to_json(papers: list[PaperResult]) -> dict[str, Any]:
    return {
        "items": [
            {
                "source": p.source,
                "source_id": p.source_id,
                "title": p.title,
                "authors": [{"name": a.name, "affiliation": a.affiliation} for a in p.authors],
                "abstract": p.abstract,
                "url": p.url,
                "published_date": str(p.published_date) if p.published_date else None,
                "doi": p.doi,
                "citation_count": p.citation_count,
            }
            for p in papers
        ]
    }


def _json_to_paper(data: dict[str, Any]) -> PaperResult:
    authors = [
        Author(
            name=str(a.get("name", "")),
            affiliation=a.get("affiliation"),
        )
        for a in (data.get("authors") or [])
    ]
    return PaperResult(
        source=str(data.get("source", "")),
        source_id=str(data.get("source_id", "")),
        title=str(data.get("title", "")),
        authors=authors,
        abstract=str(data.get("abstract", "")),
        url=str(data.get("url", "")),
        published_date=data.get("published_date"),
        doi=data.get("doi"),
        citation_count=data.get("citation_count"),
    )


def _evaluation_to_json(evaluation: EvaluationResult | None) -> dict[str, Any] | None:
    if evaluation is None:
        return None
    return dataclasses.asdict(evaluation)


def _json_to_evaluation(data: dict[str, Any]) -> EvaluationResult:
    return EvaluationResult(
        retrieval_score=float(data.get("retrieval_score", 0)),
        citation_score=float(data.get("citation_score", 0)),
        factual_grounding_score=float(data.get("factual_grounding_score", 0)),
        relevance_score=float(data.get("relevance_score", 0)),
        completeness_score=float(data.get("completeness_score", 0)),
        overall_score=float(data.get("overall_score", 0)),
        strengths=list(data.get("strengths") or []),
        weaknesses=list(data.get("weaknesses") or []),
        summary=str(data.get("summary", "")),
    )
