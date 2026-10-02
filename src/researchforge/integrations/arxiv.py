"""arXiv research provider.

arXiv's API returns Atom XML feeds. No API key required.
Docs: https://info.arxiv.org/help/api/index.html
Rate limit: no more than 1 request every 3 seconds.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import time
import weakref
import xml.etree.ElementTree as ET
from datetime import date

import httpx

from researchforge.integrations.base import ProviderError, ResearchProvider
from researchforge.integrations.models import (
    Author,
    PaperResult,
    SearchQuery,
    SearchResponse,
)

ARXIV_API_URL = "https://export.arxiv.org/api/query"

ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

MIN_REQUEST_INTERVAL = 3.0
_QUERY_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "during",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "vs",
        "with",
        "without",
        "how",
        "what",
        "does",
        "do",
        "is",
        "are",
    }
)

_throttle_locks: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = (
    weakref.WeakKeyDictionary()
)
_last_request_at = 0.0


MAX_AND_TERMS = 4


def build_search_query(text: str) -> str:
    """AND-join the leading terms; a bare ``all:a b c`` is parsed as ``all:a OR b OR c``.

    Capped because arXiv returns nothing once five or more terms are all required.
    """
    terms = [
        t
        for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", text)
        if t.lower() not in _QUERY_STOP_WORDS and not t.isdigit()
    ]
    if not terms:
        return f"all:{text}"
    return " AND ".join(f"all:{t}" for t in terms[:MAX_AND_TERMS])


async def _wait_for_slot() -> None:
    global _last_request_at
    loop = asyncio.get_running_loop()
    lock = _throttle_locks.setdefault(loop, asyncio.Lock())
    async with lock:
        wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at = time.monotonic()


def _text(element: ET.Element, tag: str, ns: str = ATOM_NS) -> str:
    child = element.find(f"{{{ns}}}{tag}")
    return (child.text or "").strip() if child is not None else ""


def _parse_entry(entry: ET.Element) -> PaperResult:
    """Parse a single Atom entry into a PaperResult."""
    raw_id = _text(entry, "id")
    arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

    authors = []
    for author_el in entry.findall(f"{{{ATOM_NS}}}author"):
        name = _text(author_el, "name")
        affiliation_el = author_el.find(f"{{{ARXIV_NS}}}affiliation")
        affiliation = (
            affiliation_el.text.strip()
            if affiliation_el is not None and affiliation_el.text
            else None
        )
        if name:
            authors.append(Author(name=name, affiliation=affiliation))

    published_str = _text(entry, "published")
    published_date = None
    if published_str:
        with contextlib.suppress(ValueError):
            published_date = date.fromisoformat(published_str[:10])

    categories = []
    for cat_el in entry.findall(f"{{{ATOM_NS}}}category"):
        term = cat_el.get("term")
        if term:
            categories.append(term)

    pdf_url = None
    for link_el in entry.findall(f"{{{ATOM_NS}}}link"):
        if link_el.get("title") == "pdf":
            pdf_url = link_el.get("href")
            break

    doi_el = entry.find(f"{{{ARXIV_NS}}}doi")
    doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

    return PaperResult(
        source="arxiv",
        source_id=arxiv_id,
        title=_text(entry, "title").replace("\n", " "),
        authors=authors,
        abstract=_text(entry, "summary").replace("\n", " ").strip(),
        url=raw_id,
        published_date=published_date,
        doi=doi,
        pdf_url=pdf_url,
        categories=categories,
    )


class ArxivProvider(ResearchProvider):
    """Search arXiv for academic papers."""

    @property
    def name(self) -> str:
        return "arxiv"

    async def search(self, query: SearchQuery) -> SearchResponse:
        sort_map = {
            "relevance": "relevance",
            "date": "lastUpdatedDate",
            "submitted": "submittedDate",
        }
        sort_by = sort_map.get(query.sort_by, "relevance")

        params: dict[str, str | int] = {
            "search_query": build_search_query(query.query),
            "start": 0,
            "max_results": min(query.max_results, 50),
            "sortBy": sort_by,
            "sortOrder": "descending",
        }

        await _wait_for_slot()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await self._request_with_retry(client, "GET", ARXIV_API_URL, params=params)

        root = ET.fromstring(response.text)

        total_el = root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults")
        total_results = int(total_el.text) if total_el is not None and total_el.text else None

        papers = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            try:
                paper = _parse_entry(entry)
                if paper.title:
                    papers.append(paper)
            except Exception as exc:
                raise ProviderError("arxiv", f"Failed to parse entry: {exc}") from exc

        return SearchResponse(
            provider="arxiv",
            query=query.query,
            total_results=total_results,
            papers=papers,
        )
