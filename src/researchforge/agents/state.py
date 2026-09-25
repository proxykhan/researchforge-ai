"""Shared state definition for the research agent graph."""

from dataclasses import dataclass
from typing import Protocol, TypedDict

from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import PaperResult


@dataclass(frozen=True)
class ResearchPlan:
    """Structured output from the Planner agent."""

    domain: str
    subtasks: list[str]
    search_queries: list[str]
    completion_criteria: str


class StatusCallback(Protocol):
    """Called by graph nodes to report progress to the service layer."""

    def __call__(self, status: ResearchStatus) -> None: ...


class ResearchState(TypedDict, total=False):
    """Typed state that flows through the research graph."""

    question: str
    plan: ResearchPlan
    search_queries: list[str]
    papers: list[PaperResult]
    synthesis: str
    error: str | None
    status_callback: StatusCallback
