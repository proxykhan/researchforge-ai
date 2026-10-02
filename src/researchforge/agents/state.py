"""Shared state definition for the research agent graph."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypedDict

from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import PaperResult

StatusCallback = Callable[[ResearchStatus], Awaitable[None]]


@dataclass(frozen=True)
class ResearchPlan:
    """Structured output from the Planner agent."""

    domain: str
    subtasks: list[str]
    search_queries: list[str]
    completion_criteria: str


@dataclass(frozen=True)
class ClaimVerification:
    """A single fact-checked claim with its verdict."""

    claim: str
    status: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass(frozen=True)
class DebateResult:
    """Outcome of the support/skeptic/judge debate."""

    topic: str
    support_argument: str
    skeptic_argument: str
    judgment: str
    conclusion: str


@dataclass(frozen=True)
class CriticResult:
    """Critic's assessment of research quality."""

    completeness_score: float
    missing_areas: list[str] = field(default_factory=list)
    weak_points: list[str] = field(default_factory=list)
    needs_more_research: bool = False
    additional_queries: list[str] = field(default_factory=list)
    feedback: str = ""


@dataclass(frozen=True)
class EvaluationResult:
    """Evaluation agent's quality assessment of the research output."""

    retrieval_score: float
    citation_score: float
    factual_grounding_score: float
    relevance_score: float
    completeness_score: float
    overall_score: float
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    summary: str = ""


class ResearchState(TypedDict, total=False):
    """Typed state that flows through the research graph."""

    question: str
    plan: ResearchPlan
    search_queries: list[str]
    searched_queries: list[str]
    papers: list[PaperResult]
    synthesis: str
    error: str | None
    status_callback: StatusCallback
    claim_verifications: list[ClaimVerification]
    debate_result: DebateResult
    critic_result: CriticResult
    evaluation: EvaluationResult
    iteration: int
