"""Researcher agent — searches providers, deduplicates, and ranks papers."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from researchforge.agents.state import ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import PaperResult, SearchQuery
from researchforge.integrations.registry import ProviderRegistry

logger = logging.getLogger(__name__)

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "but",
        "and",
        "or",
        "if",
        "while",
        "about",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "am",
        "it",
        "its",
        "my",
        "we",
        "our",
        "your",
        "his",
        "her",
        "their",
        "no",
    }
)


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text, filtering stop words."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOP_WORDS}


def _relevance_score(paper: PaperResult, keywords: set[str]) -> int:
    """Count keyword matches in paper title + abstract."""
    text = f"{paper.title} {paper.abstract or ''}".lower()
    return sum(1 for kw in keywords if kw in text)


@dataclass
class ResearcherAgent:
    """Searches academic sources, deduplicates, and ranks results."""

    registry: ProviderRegistry
    max_results_per_query: int = 5

    async def run(self, state: ResearchState) -> ResearchState:
        queries = state.get("search_queries", [])
        question = state.get("question", "")
        callback = state.get("status_callback")
        if callback:
            await callback(ResearchStatus.RESEARCHING)

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

        keywords = _extract_keywords(question)
        ranked = self._rank_papers(all_papers, keywords)
        logger.info("Researcher found %d unique papers from %d queries", len(ranked), len(queries))
        return {"papers": ranked}

    @staticmethod
    def _rank_papers(papers: list[PaperResult], keywords: set[str]) -> list[PaperResult]:
        """Rank papers by relevance to the question, then by abstract and citations.

        Papers with zero keyword overlap are filtered out when at least some
        papers match. Falls back to keeping all papers if none match.
        """

        def score(p: PaperResult) -> tuple[int, int, int]:
            relevance = _relevance_score(p, keywords) if keywords else 0
            has_abstract = 1 if p.abstract else 0
            citations = p.citation_count or 0
            return (relevance, has_abstract, citations)

        scored = [(p, score(p)) for p in papers]
        scored.sort(key=lambda x: x[1], reverse=True)

        if keywords:
            relevant = [p for p, s in scored if s[0] > 0]
            if relevant:
                return relevant

        return [p for p, _ in scored]
