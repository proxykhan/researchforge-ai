"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from researchforge import __version__
from researchforge.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=__version__)


@router.get("/ready", response_model=HealthResponse)
async def ready() -> HealthResponse:
    return HealthResponse(version=__version__)
