"""Research endpoints — submit questions and retrieve results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from researchforge.api.schemas import (
    ResearchDetail,
    ResearchRequest,
    ResearchSourcesResponse,
    ResearchSummary,
    StatusResponse,
)
from researchforge.services.research import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


def _get_service(request: Request) -> ResearchService:
    return request.app.state.research_service  # type: ignore[no-any-return]


@router.post("", response_model=ResearchSummary, status_code=201)
async def create_research(body: ResearchRequest, request: Request) -> ResearchSummary:
    """Submit a new research question."""
    service = _get_service(request)
    return service.create_job(body.question)


@router.get("/{research_id}", response_model=ResearchDetail)
async def get_research(research_id: str, request: Request) -> ResearchDetail:
    """Get full details for a research job."""
    service = _get_service(request)
    result = service.get_job(research_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result


@router.get("/{research_id}/status", response_model=StatusResponse)
async def get_research_status(research_id: str, request: Request) -> StatusResponse:
    """Lightweight status check for a research job."""
    service = _get_service(request)
    result = service.get_status(research_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result


@router.get("/{research_id}/sources", response_model=ResearchSourcesResponse)
async def get_research_sources(research_id: str, request: Request) -> ResearchSourcesResponse:
    """Get papers found during research."""
    service = _get_service(request)
    result = service.get_sources(research_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result
