"""Pydantic models for API request/response validation."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Research job statuses (from the spec)
# ---------------------------------------------------------------------------


class ResearchStatus(enum.StrEnum):
    """Lifecycle states of a research job."""

    QUEUED = "queued"
    PLANNING = "planning"
    RESEARCHING = "researching"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ResearchRequest(BaseModel):
    """POST body to start a new research job."""

    question: str = Field(min_length=3, max_length=2000, description="The research question")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PaperResponse(BaseModel):
    """A single paper in API responses."""

    source: str
    source_id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    published_date: str | None = None
    doi: str | None = None
    citation_count: int | None = None


class ResearchSummary(BaseModel):
    """Returned by POST (creation) and list endpoints."""

    id: str
    question: str
    status: ResearchStatus
    created_at: datetime


class ResearchDetail(BaseModel):
    """Full research result returned by GET /research/{id}."""

    id: str
    question: str
    status: ResearchStatus
    created_at: datetime
    completed_at: datetime | None = None
    search_queries: list[str] = Field(default_factory=list)
    paper_count: int = 0
    synthesis: str | None = None
    error: str | None = None


class ResearchSourcesResponse(BaseModel):
    """Papers found during research."""

    id: str
    papers: list[PaperResponse]


class StatusResponse(BaseModel):
    """Lightweight status check."""

    id: str
    status: ResearchStatus


# ---------------------------------------------------------------------------
# Standard error response
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Consistent error body across all endpoints."""

    detail: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
