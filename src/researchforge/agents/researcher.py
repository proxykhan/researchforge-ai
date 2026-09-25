"""Researcher agent — searches providers, deduplicates, and ranks papers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from researchforge.agents.state import ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import PaperResult, SearchQuery
from researchforge.integrations.registry import ProviderRegistry

logger = logging.getLogger(__name__)


@dataclass
class ResearcherAgent:
    """Searches academic sources, deduplicates, and ranks results."""

    registry: ProviderRegistry
    max_results_per_query: int = 5

    async def run(self, state: ResearchState) -> ResearchState:
        queries = state.get("search_queries", [])
        callback = state.get("status_callback")
        if callback:
            callback(ResearchStatus.RESEARCHING)

        if not queries:
            return {"papers": [], "error": "No search queries to execute"}

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

        ranked = self._rank_papers(all_papers)
        logger.info("Researcher found %d unique papers from %d queries", len(ranked), len(queries))
        return {"papers": ranked}

    @staticmethod
    def _rank_papers(papers: list[PaperResult]) -> list[PaperResult]:
        """Rank papers by a simple relevance heuristic.

        Papers with abstracts and higher citation counts rank higher.
        """

        def score(p: PaperResult) -> tuple[int, int]:
            has_abstract = 1 if p.abstract else 0
            citations = p.citation_count or 0
            return (has_abstract, citations)

        return sorted(papers, key=score, reverse=True)
