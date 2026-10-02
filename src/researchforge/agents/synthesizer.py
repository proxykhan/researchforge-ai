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
You are a research synthesis agent that writes for a general audience. \
Given a research question, a research plan, and a list of academic papers, \
produce a clear, easy-to-read research summary that anyone can understand.

WRITING STYLE — CRITICAL:
- Write as if explaining to a smart friend who has NO background in this field.
- Use plain, everyday language. Replace jargon with simple explanations.
- Use short sentences and short paragraphs.
- Lead with the big-picture answer before diving into details.
- You may use an analogy to explain a concept, but never present an analogy \
or general knowledge as a research finding.

GROUNDING — CRITICAL:
- Every finding must come from the papers listed below. Do not add facts, \
numbers, studies, or authors that are not in that list.
- Cite only papers from the list, using their exact title or (First author, Year).
- Ignore any listed paper that does not actually address the research question.
- If the papers do not answer part of the question, say so plainly under \
"What's Still Unknown" instead of filling the gap.

STRUCTURE (use these exact headings):
## Key Takeaway
One-paragraph plain-English answer to the research question.

## What We Know
The main findings, written as a numbered list. Each point should be \
one or two simple sentences. Cite the source in parentheses like (Author, Year) \
or (Paper Title).

## How It Works
Explain the core concepts or mechanisms in simple terms. Use analogies. \
Skip this section if not applicable.

## What's Still Unknown
Bullet list of open questions and gaps, written simply.

## Bottom Line
Two to three sentences summarizing the practical takeaway.

RULES:
- NO dense comparison tables with technical jargon.
- NO walls of text or long academic paragraphs.
- NO unexplained acronyms — always spell out and explain on first use.
- Keep the total summary under 550 words.
- Use **bold** for key terms when first introduced.\
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
            await callback(ResearchStatus.SYNTHESIZING)

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
        parts.append(
            "\nSynthesize these findings into a clear, simple summary "
            "that a non-expert can easily understand. Use plain language, "
            "short sentences, and avoid technical jargon."
        )

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
