"""Researcher agent — searches providers, deduplicates, and ranks papers."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from researchforge.agents.state import ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import PaperResult, SearchQuery
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

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


SCREEN_SYSTEM = """\
You screen academic search results for relevance to a research question.

A paper is RELEVANT only if its title/abstract shows it directly studies the \
question's topic or one of its core sub-topics. A paper is NOT relevant if it \
merely shares a word with the question (e.g. "sleep" in a machine-learning \
algorithm name when the question is about human sleep), is from an unrelated \
field, or is an editorial, erratum, or review comment.

Return JSON only: {"relevant": [list of candidate numbers]}. Return an empty \
list if none are relevant.\
"""

MAX_SCREEN_CANDIDATES = 30

_BOOLEAN_OPERATORS = frozenset({"AND", "OR", "NOT"})
_YEAR_TOKEN = re.compile(r"^\d{4}(?:[.\-]+\d{4})?$")
_UNICODE_DASHES = re.compile(f"[{chr(0x2010)}-{chr(0x2015)}]")


def clean_query(text: str) -> str:
    """Strip search-engine syntax (quotes, boolean operators, years) LLMs tend to emit.

    None of the providers support that syntax; they treat each token as a search
    word, so ``"x" AND y 2022..2024`` matches far fewer relevant papers than ``x y``.
    """
    text = _UNICODE_DASHES.sub("-", text)
    text = re.sub(r"[\"'()\[\]{}]", " ", text)
    tokens = [
        t
        for t in text.split()
        if t not in _BOOLEAN_OPERATORS and not _YEAR_TOKEN.match(t.strip(".,;:"))
    ]
    cleaned = " ".join(tokens)
    return cleaned or text.strip()


def _dedup_keys(paper: PaperResult) -> set[str]:
    """Keys that identify the same work across providers (source id, DOI, title)."""
    keys = {f"id:{paper.source}:{paper.source_id}"}
    if paper.doi:
        keys.add(f"doi:{paper.doi.lower()}")
    title = re.sub(r"[^a-z0-9]", "", paper.title.lower())
    if title:
        keys.add(f"title:{title}")
    return keys


def _parse_indices(content: str, count: int) -> list[int] | None:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    raw = data.get("relevant") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    indices: list[int] = []
    for item in raw:
        if isinstance(item, int) and 1 <= item <= count and item - 1 not in indices:
            indices.append(item - 1)
    return indices


@dataclass
class ResearcherAgent:
    """Searches academic sources, deduplicates, screens for relevance, and ranks."""

    registry: ProviderRegistry
    llm: LLMProvider | None = None
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    max_results_per_query: int = 5

    async def run(self, state: ResearchState) -> ResearchState:
        queries = state.get("search_queries", [])
        question = state.get("question", "")
        callback = state.get("status_callback")
        if callback:
            await callback(ResearchStatus.RESEARCHING)

        if not queries:
            return {"papers": [], "error": "No search queries to execute"}

        already_searched = set(state.get("searched_queries", []))
        new_queries = [q for q in queries if q not in already_searched]
        existing = list(state.get("papers", [])) if already_searched else []
        if not new_queries:
            return {}

        responses_per_query = await asyncio.gather(
            *(
                self.registry.search(
                    SearchQuery(query=clean_query(q), max_results=self.max_results_per_query)
                )
                for q in new_queries
            )
        )

        seen: set[str] = set()
        for p in existing:
            seen |= _dedup_keys(p)
        candidates: list[PaperResult] = []
        for responses in responses_per_query:
            for resp in responses:
                for paper in resp.papers:
                    keys = _dedup_keys(paper)
                    if seen.isdisjoint(keys):
                        seen |= keys
                        candidates.append(paper)

        keywords = _extract_keywords(question)
        ranked = self._rank_papers(candidates, keywords, drop_unmatched=self.llm is None)
        screened = await self._screen(question, ranked)
        papers = existing + screened
        logger.info(
            "Researcher kept %d of %d new papers from %d queries (%d total)",
            len(screened),
            len(candidates),
            len(new_queries),
            len(papers),
        )
        return {
            "papers": papers,
            "searched_queries": sorted(already_searched | set(new_queries)),
        }

    async def _screen(self, question: str, ranked: list[PaperResult]) -> list[PaperResult]:
        """Ask the LLM which candidates actually address the question."""
        if self.llm is None or not ranked:
            return ranked

        candidates = ranked[:MAX_SCREEN_CANDIDATES]
        lines = []
        for i, p in enumerate(candidates, 1):
            snippet = (p.abstract or "")[:160]
            lines.append(f"[{i}] {p.title}" + (f" — {snippet}" if snippet else ""))
        prompt = f"Research question: {question}\n\nCandidates:\n" + "\n".join(lines)

        config = LLMConfig(model=self.llm_config.model, max_tokens=512, system=SCREEN_SYSTEM)
        try:
            response = await self.llm.complete(
                messages=[Message(role="user", content=prompt)], config=config
            )
        except Exception:
            logger.warning("Relevance screen failed; using keyword ranking", exc_info=True)
            return ranked

        indices = _parse_indices(response.content, len(candidates))
        if indices is None:
            logger.warning("Relevance screen returned unparseable output; using keyword ranking")
            return ranked
        keep = set(indices)
        return [p for i, p in enumerate(candidates) if i in keep]

    @staticmethod
    def _rank_papers(
        papers: list[PaperResult], keywords: set[str], *, drop_unmatched: bool = True
    ) -> list[PaperResult]:
        """Rank papers by keyword overlap with the question, then abstract and citations.

        With ``drop_unmatched``, zero-overlap papers are removed when at least one paper matches.
        """

        def score(p: PaperResult) -> tuple[int, int, int]:
            relevance = _relevance_score(p, keywords) if keywords else 0
            has_abstract = 1 if p.abstract else 0
            citations = p.citation_count or 0
            return (relevance, has_abstract, citations)

        scored = [(p, score(p)) for p in papers]
        scored.sort(key=lambda x: x[1], reverse=True)

        if keywords and drop_unmatched:
            relevant = [p for p, s in scored if s[0] > 0]
            if relevant:
                return relevant

        return [p for p, _ in scored]
