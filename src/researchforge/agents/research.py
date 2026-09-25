"""Single research agent built on LangGraph.

The agent takes a research question and runs a three-step workflow:
  1. plan_research  - LLM generates targeted search queries from the question
  2. execute_search - provider registry runs the queries concurrently
  3. synthesize     - LLM produces a structured summary from the results
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import END, StateGraph

from researchforge.integrations.models import PaperResult, SearchQuery
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ResearchState(TypedDict, total=False):
    """Typed state that flows through the research graph."""

    question: str
    search_queries: list[str]
    papers: list[PaperResult]
    synthesis: str
    error: str | None


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

PLAN_SYSTEM = (
    "You are a research planning assistant. Given a research question, "
    "generate 2-4 focused search queries that together cover the topic well. "
    "Return ONLY a JSON array of query strings, no other text."
)

SYNTHESIZE_SYSTEM = (
    "You are a research synthesis assistant. Given a research question and "
    "a list of academic papers, write a concise summary that answers the "
    "question. Cite papers by their title. If no relevant papers were found, "
    "say so clearly."
)


@dataclass
class ResearchNodes:
    """Holds the LLM and registry so node functions can access them."""

    llm: LLMProvider
    registry: ProviderRegistry
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    max_results_per_query: int = 5

    async def plan_research(self, state: ResearchState) -> ResearchState:
        """Use the LLM to turn the question into search queries."""
        question = state["question"]

        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=1024,
            system=PLAN_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=question)],
            config=config,
        )

        try:
            queries = json.loads(response.content)
            if not isinstance(queries, list):
                queries = [question]
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON plan, falling back to raw question")
            queries = [question]

        return {"search_queries": [str(q) for q in queries]}

    async def execute_search(self, state: ResearchState) -> ResearchState:
        """Run each search query through the provider registry."""
        queries = state.get("search_queries", [])
        if not queries:
            return {"papers": [], "error": "No search queries generated"}

        all_papers: list[PaperResult] = []
        seen_ids: set[str] = set()

        for query_text in queries:
            query = SearchQuery(query=query_text, max_results=self.max_results_per_query)
            responses = await self.registry.search(query)
            for resp in responses:
                for paper in resp.papers:
                    paper_id = f"{paper.source}:{paper.source_id}"
                    if paper_id not in seen_ids:
                        seen_ids.add(paper_id)
                        all_papers.append(paper)

        return {"papers": all_papers}

    async def synthesize(self, state: ResearchState) -> ResearchState:
        """Use the LLM to synthesize findings into a summary."""
        papers = state.get("papers", [])
        question = state["question"]

        if not papers:
            return {"synthesis": "No papers were found for this research question."}

        papers_text = _format_papers_for_llm(papers)
        prompt = (
            f"Research question: {question}\n\n"
            f"Papers found ({len(papers)} total):\n{papers_text}\n\n"
            "Please synthesize these findings into a concise research summary."
        )

        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=self.llm_config.max_tokens,
            system=SYNTHESIZE_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=prompt)],
            config=config,
        )

        return {"synthesis": response.content}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_research_graph(
    llm: LLMProvider,
    registry: ProviderRegistry,
    llm_config: LLMConfig | None = None,
) -> StateGraph[ResearchState]:
    """Create and compile the research agent graph."""
    nodes = ResearchNodes(
        llm=llm,
        registry=registry,
        llm_config=llm_config or LLMConfig(),
    )

    graph = StateGraph(ResearchState)
    graph.add_node("plan_research", nodes.plan_research)
    graph.add_node("execute_search", nodes.execute_search)
    graph.add_node("synthesize", nodes.synthesize)

    graph.set_entry_point("plan_research")
    graph.add_edge("plan_research", "execute_search")
    graph.add_edge("execute_search", "synthesize")
    graph.add_edge("synthesize", END)

    return graph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_papers_for_llm(papers: list[PaperResult], max_papers: int = 20) -> str:
    """Format papers into a readable string for the LLM."""
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
