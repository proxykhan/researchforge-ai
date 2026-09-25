"""Crossref research provider.

Docs: https://api.crossref.org/swagger-ui/index.html
Rate limit: polite pool (faster) if you provide a mailto in the User-Agent.
No API key required.
"""

from __future__ import annotations

from datetime import date

import httpx

from researchforge.integrations.base import ResearchProvider
from researchforge.integrations.models import (
    Author,
    PaperResult,
    SearchQuery,
    SearchResponse,
)

CROSSREF_API_URL = "https://api.crossref.org/works"
USER_AGENT = "ResearchForgeAI/0.1 (mailto:researchforge@example.com)"


def _parse_date_parts(date_parts: list[list[int]]) -> date | None:
    """Parse Crossref date-parts format like [[2024, 1, 15]]."""
    if not date_parts or not date_parts[0]:
        return None
    parts = date_parts[0]
    try:
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _parse_item(item: dict[str, object]) -> PaperResult | None:
    """Parse a Crossref work item into a PaperResult."""
    titles = item.get("title", [])
    if not isinstance(titles, list) or not titles:
        return None
    title = str(titles[0])
    if not title:
        return None

    authors = []
    author_list = item.get("author", [])
    if isinstance(author_list, list):
        for a in author_list:
            if isinstance(a, dict):
                given = a.get("given", "")
                family = a.get("family", "")
                name = f"{given} {family}".strip()
                affil_list = a.get("affiliation", [])
                affiliation = None
                if isinstance(affil_list, list) and affil_list:
                    first = affil_list[0]
                    if isinstance(first, dict):
                        affiliation = first.get("name")
                if name:
                    authors.append(Author(name=name, affiliation=affiliation))

    published_date = None
    for date_field in ("published-print", "published-online", "created"):
        date_obj = item.get(date_field)
        if isinstance(date_obj, dict):
            parts = date_obj.get("date-parts")
            if isinstance(parts, list):
                published_date = _parse_date_parts(parts)
                if published_date:
                    break

    doi = item.get("DOI")
    url = item.get("URL", "")
    if not url and doi:
        url = f"https://doi.org/{doi}"

    abstract = ""
    raw_abstract = item.get("abstract")
    if isinstance(raw_abstract, str):
        abstract = raw_abstract.replace("<jats:p>", "").replace("</jats:p>", "").strip()

    categories = []
    subjects = item.get("subject", [])
    if isinstance(subjects, list):
        categories = [s for s in subjects if isinstance(s, str)]

    citation_count = item.get("is-referenced-by-count")

    return PaperResult(
        source="crossref",
        source_id=str(doi) if doi else "",
        title=title,
        authors=authors,
        abstract=abstract,
        url=str(url),
        published_date=published_date,
        doi=str(doi) if doi else None,
        categories=categories,
        citation_count=int(str(citation_count)) if citation_count is not None else None,
    )


class CrossrefProvider(ResearchProvider):
    """Search Crossref for academic papers."""

    @property
    def name(self) -> str:
        return "crossref"

    async def search(self, query: SearchQuery) -> SearchResponse:
        params: dict[str, str | int] = {
            "query": query.query,
            "rows": min(query.max_results, 100),
        }

        sort = "relevance" if query.sort_by == "relevance" else "published"
        params["sort"] = sort
        params["order"] = "desc"

        filters: list[str] = []
        if query.year_from:
            filters.append(f"from-pub-date:{query.year_from}")
        if query.year_to:
            filters.append(f"until-pub-date:{query.year_to}")
        if filters:
            params["filter"] = ",".join(filters)

        headers = {"User-Agent": USER_AGENT}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await self._request_with_retry(
                client, "GET", CROSSREF_API_URL, params=params, headers=headers
            )

        data = response.json()
        message = data.get("message", {})
        total = message.get("total-results", 0)

        papers = []
        for item in message.get("items", []):
            paper = _parse_item(item)
            if paper:
                papers.append(paper)

        return SearchResponse(
            provider="crossref",
            query=query.query,
            total_results=total,
            papers=papers,
        )
