"""Tests for the research agent graph."""

from __future__ import annotations

from researchforge.agents.research import (
    ResearchNodes,
    ResearchState,
    _format_papers_for_llm,
    build_research_graph,
)
from researchforge.integrations.models import (
    Author,
    PaperResult,
    SearchQuery,
    SearchResponse,
)
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, LLMResponse, Message, TokenUsage

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

FAKE_USAGE = TokenUsage(input_tokens=10, output_tokens=20)


class FakeLLM(LLMProvider):
    """LLM that returns canned responses based on call order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_index = 0
        self.calls: list[list[Message]] = []

    @property
    def name(self) -> str:
        return "fake"

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        self.calls.append(messages)
        content = self._responses[self._call_index]
        self._call_index += 1
        return LLMResponse(content=content, model="fake-model", usage=FAKE_USAGE)


class FakeSearchProvider:
    """Mimics a ResearchProvider for registry use."""

    def __init__(self, provider_name: str, papers: list[PaperResult]) -> None:
        self._name = provider_name
        self._papers = papers

    @property
    def name(self) -> str:
        return self._name

    async def search(self, query: SearchQuery) -> SearchResponse:
        return SearchResponse(
            provider=self._name,
            query=query.query,
            total_results=len(self._papers),
            papers=self._papers,
        )


SAMPLE_PAPER = PaperResult(
    source="test",
    source_id="123",
    title="Deep Learning for NLP",
    authors=[Author(name="Alice Smith")],
    abstract="A comprehensive survey of deep learning methods in NLP.",
    url="https://example.com/paper",
    published_date=None,
    citation_count=42,
)


# ---------------------------------------------------------------------------
# Node tests
# ---------------------------------------------------------------------------


class TestPlanResearch:
    async def test_parses_json_queries(self):
        llm = FakeLLM(responses=['["transformers NLP", "attention mechanisms"]'])
        registry = ProviderRegistry(providers=[])
        nodes = ResearchNodes(llm=llm, registry=registry)

        result = await nodes.plan_research(ResearchState(question="How do transformers work?"))

        assert result["search_queries"] == ["transformers NLP", "attention mechanisms"]

    async def test_falls_back_on_invalid_json(self):
        llm = FakeLLM(responses=["Just some text, not JSON"])
        registry = ProviderRegistry(providers=[])
        nodes = ResearchNodes(llm=llm, registry=registry)

        result = await nodes.plan_research(ResearchState(question="How do transformers work?"))

        assert result["search_queries"] == ["How do transformers work?"]

    async def test_falls_back_on_non_list_json(self):
        llm = FakeLLM(responses=['{"not": "a list"}'])
        registry = ProviderRegistry(providers=[])
        nodes = ResearchNodes(llm=llm, registry=registry)

        result = await nodes.plan_research(ResearchState(question="test question"))

        assert result["search_queries"] == ["test question"]


class TestExecuteSearch:
    async def test_collects_papers(self):
        llm = FakeLLM(responses=[])
        fake_provider = FakeSearchProvider("test_prov", [SAMPLE_PAPER])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        nodes = ResearchNodes(llm=llm, registry=registry)
        result = await nodes.execute_search(
            ResearchState(question="test", search_queries=["deep learning NLP"])
        )

        assert len(result["papers"]) == 1
        assert result["papers"][0].title == "Deep Learning for NLP"

    async def test_deduplicates_papers(self):
        llm = FakeLLM(responses=[])
        fake_provider = FakeSearchProvider("test_prov", [SAMPLE_PAPER])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        nodes = ResearchNodes(llm=llm, registry=registry)
        result = await nodes.execute_search(
            ResearchState(
                question="test",
                search_queries=["query one", "query two"],
            )
        )

        assert len(result["papers"]) == 1

    async def test_empty_queries(self):
        llm = FakeLLM(responses=[])
        registry = ProviderRegistry(providers=[])
        nodes = ResearchNodes(llm=llm, registry=registry)

        result = await nodes.execute_search(ResearchState(question="test", search_queries=[]))

        assert result["papers"] == []
        assert result["error"] == "No search queries generated"


class TestSynthesize:
    async def test_produces_synthesis(self):
        llm = FakeLLM(responses=["Here is a summary of the findings."])
        registry = ProviderRegistry(providers=[])
        nodes = ResearchNodes(llm=llm, registry=registry)

        result = await nodes.synthesize(ResearchState(question="test", papers=[SAMPLE_PAPER]))

        assert "summary" in result["synthesis"]
        assert len(llm.calls) == 1

    async def test_no_papers_message(self):
        llm = FakeLLM(responses=[])
        registry = ProviderRegistry(providers=[])
        nodes = ResearchNodes(llm=llm, registry=registry)

        result = await nodes.synthesize(ResearchState(question="test", papers=[]))

        assert "No papers" in result["synthesis"]
        assert len(llm.calls) == 0


# ---------------------------------------------------------------------------
# Graph tests
# ---------------------------------------------------------------------------


class TestBuildResearchGraph:
    def test_graph_compiles(self):
        llm = FakeLLM(responses=[])
        registry = ProviderRegistry(providers=[])
        graph = build_research_graph(llm, registry)
        compiled = graph.compile()
        assert compiled is not None

    async def test_full_graph_execution(self):
        llm = FakeLLM(
            responses=[
                '["deep learning NLP"]',
                "Summary: Deep learning is transforming NLP.",
            ]
        )
        fake_provider = FakeSearchProvider("test_prov", [SAMPLE_PAPER])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        graph = build_research_graph(llm, registry)
        compiled = graph.compile()

        result = await compiled.ainvoke({"question": "How does deep learning help NLP?"})

        assert result["search_queries"] == ["deep learning NLP"]
        assert len(result["papers"]) == 1
        assert "Deep learning" in result["synthesis"]


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestFormatPapersForLLM:
    def test_formats_paper(self):
        text = _format_papers_for_llm([SAMPLE_PAPER])
        assert "Deep Learning for NLP" in text
        assert "Alice Smith" in text
        assert "42" in text

    def test_truncates_long_abstract(self):
        paper = PaperResult(
            source="test",
            source_id="456",
            title="Long Abstract Paper",
            authors=[],
            abstract="x" * 500,
            url="https://example.com",
        )
        text = _format_papers_for_llm([paper])
        assert "..." in text

    def test_respects_max_papers(self):
        papers = [
            PaperResult(
                source="test",
                source_id=str(i),
                title=f"Paper {i}",
                authors=[],
                abstract="",
                url="",
            )
            for i in range(30)
        ]
        text = _format_papers_for_llm(papers, max_papers=5)
        assert "Paper 0" in text
        assert "Paper 4" in text
        assert "Paper 5" not in text
