"""Normalized data models for research sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Author:
    """A paper author."""

    name: str
    affiliation: str | None = None


@dataclass(frozen=True)
class PaperResult:
    """A normalized research paper from any provider.

    Every provider maps its response into this common shape so the rest
    of the application never deals with provider-specific formats.
    """

    source: str
    source_id: str
    title: str
    authors: list[Author]
    abstract: str
    url: str
    published_date: date | None = None
    doi: str | None = None
    pdf_url: str | None = None
    categories: list[str] = field(default_factory=list)
    citation_count: int | None = None

    @property
    def display_authors(self) -> str:
        if not self.authors:
            return "Unknown"
        names = [a.name for a in self.authors[:3]]
        suffix = " et al." if len(self.authors) > 3 else ""
        return ", ".join(names) + suffix


@dataclass(frozen=True)
class SearchQuery:
    """A search request to a research provider."""

    query: str
    max_results: int = 10
    sort_by: str = "relevance"
    year_from: int | None = None
    year_to: int | None = None


@dataclass(frozen=True)
class SearchResponse:
    """The result of a provider search."""

    provider: str
    query: str
    total_results: int | None
    papers: list[PaperResult]
