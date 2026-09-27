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


@router.get("", response_model=list[ResearchSummary])
async def list_research(request: Request) -> list[ResearchSummary]:
    """List all research jobs, newest first."""
    service = _get_service(request)
    return service.list_jobs()


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


@router.get("/{research_id}/report", response_model=ResearchDetail)
async def get_research_report(research_id: str, request: Request) -> ResearchDetail:
    """Get the final research report."""
    service = _get_service(request)
    result = service.get_report(research_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result


@router.post("/{research_id}/cancel", response_model=StatusResponse)
async def cancel_research(research_id: str, request: Request) -> StatusResponse:
    """Cancel a running research job."""
    service = _get_service(request)
    cancelled = service.cancel_job(research_id)
    if not cancelled:
        status = service.get_status(research_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Research job not found")
        raise HTTPException(
            status_code=409,
            detail="Job cannot be cancelled (already completed or failed)",
        )
    result = service.get_status(research_id)
    assert result is not None
    return result
