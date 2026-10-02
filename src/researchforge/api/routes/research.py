"""Research endpoints — submit questions and retrieve results."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from researchforge.api.schemas import (
    ResearchDetail,
    ResearchRequest,
    ResearchSourcesResponse,
    ResearchSummary,
    StatusResponse,
)
from researchforge.auth.dependencies import AuthenticatedUser
from researchforge.cache.rate_limiter import RateLimiter
from researchforge.services.research import ResearchService

router = APIRouter(prefix="/research", tags=["research"])

_bearer_scheme = HTTPBearer(auto_error=False)
_bearer_security = Security(_bearer_scheme)


def _get_service(request: Request) -> ResearchService:
    return request.app.state.research_service  # type: ignore[no-any-return]


async def _get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = _bearer_security,
) -> AuthenticatedUser:
    """Authenticate, then apply rate limiting."""
    from researchforge.auth.dependencies import AuthDependency

    auth: AuthDependency = request.app.state.auth_dependency
    user = await auth(request, credentials)

    limiter: RateLimiter | None = getattr(request.app.state, "rate_limiter", None)
    if limiter is not None:
        allowed = await limiter.check(user.id)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return user


_auth = Depends(_get_current_user)


@router.post("", response_model=ResearchSummary, status_code=201)
async def create_research(
    body: ResearchRequest,
    request: Request,
    user: AuthenticatedUser = _auth,
) -> ResearchSummary:
    """Submit a new research question."""
    service = _get_service(request)
    return await service.create_job(body.question, user_id=user.id)


@router.get("", response_model=list[ResearchSummary])
async def list_research(
    request: Request,
    user: AuthenticatedUser = _auth,
) -> list[ResearchSummary]:
    """List the current user's research jobs, newest first."""
    service = _get_service(request)
    return await service.list_jobs(user_id=user.id)


@router.get("/{research_id}", response_model=ResearchDetail)
async def get_research(
    research_id: str,
    request: Request,
    user: AuthenticatedUser = _auth,
) -> ResearchDetail:
    """Get full details for a research job."""
    service = _get_service(request)
    result = await service.get_job(research_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result


@router.get("/{research_id}/status", response_model=StatusResponse)
async def get_research_status(
    research_id: str,
    request: Request,
    user: AuthenticatedUser = _auth,
) -> StatusResponse:
    """Lightweight status check for a research job."""
    service = _get_service(request)
    result = await service.get_status(research_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result


@router.get("/{research_id}/sources", response_model=ResearchSourcesResponse)
async def get_research_sources(
    research_id: str,
    request: Request,
    user: AuthenticatedUser = _auth,
) -> ResearchSourcesResponse:
    """Get papers found during research."""
    service = _get_service(request)
    result = await service.get_sources(research_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result


@router.get("/{research_id}/report", response_model=ResearchDetail)
async def get_research_report(
    research_id: str,
    request: Request,
    user: AuthenticatedUser = _auth,
) -> ResearchDetail:
    """Get the final research report."""
    service = _get_service(request)
    result = await service.get_report(research_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return result


@router.post("/{research_id}/cancel", response_model=StatusResponse)
async def cancel_research(
    research_id: str,
    request: Request,
    user: AuthenticatedUser = _auth,
) -> StatusResponse:
    """Cancel a running research job."""
    service = _get_service(request)
    cancelled = await service.cancel_job(research_id, user_id=user.id)
    if not cancelled:
        status = await service.get_status(research_id, user_id=user.id)
        if status is None:
            raise HTTPException(status_code=404, detail="Research job not found")
        raise HTTPException(
            status_code=409,
            detail="Job cannot be cancelled (already completed or failed)",
        )
    result = await service.get_status(research_id, user_id=user.id)
    assert result is not None
    return result
