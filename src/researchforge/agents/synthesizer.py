"""Synthesizer agent — produces a structured research summary with citations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from researchforge.agents.state import ResearchPlan, ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import PaperResult
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)

SYNTHESIZER_SYSTEM = """\
You are a research synthesis agent. Given a research question, a research plan, \
and a list of academic papers, produce a structured research summary.

Your summary MUST:
1. Answer the research question using evidence from the papers.
2. Cite papers by their title in square brackets, e.g. [Paper Title].
3. Clearly distinguish evidence from your interpretation.
4. State uncertainty where evidence is limited or conflicting.
5. Identify limitations and gaps in the available research.

Structure your response with clear sections. Be concise but thorough.\
"""


@dataclass
class SynthesizerAgent:
    """Produces a citation-grounded research summary."""

    llm: LLMProvider
    llm_config: LLMConfig = field(default_factory=LLMConfig)

    async def run(self, state: ResearchState) -> ResearchState:
        papers = state.get("papers", [])
        question = state["question"]
        plan = state.get("plan")
        callback = state.get("status_callback")
        if callback:
            callback(ResearchStatus.SYNTHESIZING)

        if not papers:
            return {"synthesis": "No papers were found for this research question."}

        prompt = self._build_prompt(question, plan, papers)

        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=self.llm_config.max_tokens,
            system=SYNTHESIZER_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=prompt)],
            config=config,
        )

        return {"synthesis": response.content}

    @staticmethod
    def _build_prompt(
        question: str,
        plan: ResearchPlan | None,
        papers: list[PaperResult],
    ) -> str:
        parts = [f"Research question: {question}"]

        if plan:
            parts.append(f"\nResearch domain: {plan.domain}")
            parts.append("Subtasks investigated:")
            for i, subtask in enumerate(plan.subtasks, 1):
                parts.append(f"  {i}. {subtask}")
            if plan.completion_criteria:
                parts.append(f"\nCompletion criteria: {plan.completion_criteria}")

        parts.append(f"\nPapers found ({len(papers)} total):")
        parts.append(_format_papers(papers))
        parts.append("\nPlease synthesize these findings into a structured research summary.")

        return "\n".join(parts)


def _format_papers(papers: list[PaperResult], max_papers: int = 20) -> str:
    lines: list[str] = []
    for i, paper in enumerate(papers[:max_papers], 1):
        parts = [f"{i}. {paper.title}"]
        if paper.authors:
            parts.append(f"   Authors: {paper.display_authors}")
        if paper.published_date:
            parts.append(f"   Date: {paper.published_date}")
        if paper.abstract:
            abstract = paper.abstract[:300] + "..." if len(paper.abstract) > 300 else paper.abstract
            parts.append(f"   Abstract: {abstract}")
        if paper.citation_count is not None:
            parts.append(f"   Citations: {paper.citation_count}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)
