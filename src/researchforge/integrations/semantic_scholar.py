"""Semantic Scholar research provider.

Docs: https://api.semanticscholar.org/
Rate limit: 1 request/sec without API key, 10 req/sec with key.
"""

from __future__ import annotations

import contextlib
import os
from datetime import date

import httpx

from researchforge.integrations.base import ResearchProvider
from researchforge.integrations.models import (
    Author,
    PaperResult,
    SearchQuery,
    SearchResponse,
)

S2_API_URL = "https://api.semanticscholar.org/graph/v1"

PAPER_FIELDS = ",".join(
    [
        "paperId",
        "title",
        "abstract",
        "authors",
        "year",
        "publicationDate",
        "externalIds",
        "url",
        "citationCount",
        "fieldsOfStudy",
        "isOpenAccess",
        "openAccessPdf",
    ]
)


def _parse_paper(data: dict[str, object]) -> PaperResult | None:
    """Parse a Semantic Scholar paper dict into a PaperResult."""
    title = data.get("title")
    if not title or not isinstance(title, str):
        return None

    authors_raw = data.get("authors", [])
    authors = []
    if isinstance(authors_raw, list):
        for a in authors_raw:
            if isinstance(a, dict):
                name = a.get("name", "")
                if name:
                    authors.append(Author(name=name))

    published_date = None
    pub_date_str = data.get("publicationDate")
    if isinstance(pub_date_str, str) and len(pub_date_str) >= 10:
        with contextlib.suppress(ValueError):
            published_date = date.fromisoformat(pub_date_str[:10])

    external_ids = data.get("externalIds")
    doi = None
    if isinstance(external_ids, dict):
        doi = external_ids.get("DOI")

    pdf_url = None
    oap = data.get("openAccessPdf")
    if isinstance(oap, dict):
        pdf_url = oap.get("url")

    categories = []
    fields = data.get("fieldsOfStudy")
    if isinstance(fields, list):
        categories = [f for f in fields if isinstance(f, str)]

    url = data.get("url", "")
    citation_count = data.get("citationCount")

    return PaperResult(
        source="semantic_scholar",
        source_id=str(data.get("paperId", "")),
        title=title,
        authors=authors,
        abstract=str(data.get("abstract", "") or ""),
        url=str(url) if url else f"https://www.semanticscholar.org/paper/{data.get('paperId', '')}",
        published_date=published_date,
        doi=str(doi) if doi else None,
        pdf_url=str(pdf_url) if pdf_url else None,
        categories=categories,
        citation_count=int(str(citation_count)) if citation_count is not None else None,
    )


class SemanticScholarProvider(ResearchProvider):
    """Search Semantic Scholar for academic papers."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    @property
    def name(self) -> str:
        return "semantic_scholar"

    async def search(self, query: SearchQuery) -> SearchResponse:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        params: dict[str, str | int] = {
            "query": query.query,
            "limit": min(query.max_results, 100),
            "fields": PAPER_FIELDS,
        }

        if query.year_from or query.year_to:
            year_range = f"{query.year_from or ''}-{query.year_to or ''}"
            params["year"] = year_range

        url = f"{S2_API_URL}/paper/search"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await self._request_with_retry(
                client, "GET", url, params=params, headers=headers
            )

        data = response.json()
        total = data.get("total", 0)

        papers = []
        for item in data.get("data", []):
            paper = _parse_paper(item)
            if paper:
                papers.append(paper)

        return SearchResponse(
            provider="semantic_scholar",
            query=query.query,
            total_results=total,
            papers=papers,
        )
