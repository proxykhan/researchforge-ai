"""Tests for the multi-agent research graph (Phase 4)."""

from __future__ import annotations

import json

from researchforge.agents.planner import PlannerAgent
from researchforge.agents.research import build_research_graph
from researchforge.agents.researcher import ResearcherAgent
from researchforge.agents.state import ResearchPlan, ResearchState
from researchforge.agents.synthesizer import SynthesizerAgent, _format_papers
from researchforge.api.schemas import ResearchStatus
from researchforge.integrations.models import Author, PaperResult, SearchQuery, SearchResponse
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


def _make_status_tracker() -> tuple[list[ResearchStatus], ResearchState]:
    """Create a status tracker and a state dict with the callback wired in."""
    statuses: list[ResearchStatus] = []

    def _track(status: ResearchStatus) -> None:
        statuses.append(status)

    state: ResearchState = {"question": "test question", "status_callback": _track}
    return statuses, state


# ---------------------------------------------------------------------------
# PlannerAgent tests
# ---------------------------------------------------------------------------


class TestPlannerAgent:
    async def test_parses_valid_json_plan(self) -> None:
        plan_json = json.dumps(
            {
                "domain": "machine learning",
                "subtasks": ["What are transformers?", "How does attention work?"],
                "search_queries": ["transformers NLP", "attention mechanisms"],
                "completion_criteria": "Explain transformers with citations",
            }
        )
        llm = FakeLLM(responses=[plan_json])
        planner = PlannerAgent(llm=llm)

        result = await planner.run(ResearchState(question="How do transformers work?"))

        assert isinstance(result["plan"], ResearchPlan)
        assert result["plan"].domain == "machine learning"
        assert result["search_queries"] == ["transformers NLP", "attention mechanisms"]
        assert len(result["plan"].subtasks) == 2

    async def test_falls_back_on_invalid_json(self) -> None:
        llm = FakeLLM(responses=["Just some text, not JSON"])
        planner = PlannerAgent(llm=llm)

        result = await planner.run(ResearchState(question="How do transformers work?"))

        plan = result["plan"]
        assert isinstance(plan, ResearchPlan)
        assert plan.domain == "general"
        assert plan.search_queries == ["How do transformers work?"]
        assert result["search_queries"] == ["How do transformers work?"]

    async def test_falls_back_on_non_object_json(self) -> None:
        llm = FakeLLM(responses=['["just", "a", "list"]'])
        planner = PlannerAgent(llm=llm)

        result = await planner.run(ResearchState(question="test question"))

        assert result["plan"].domain == "general"
        assert result["search_queries"] == ["test question"]

    async def test_handles_empty_subtasks(self) -> None:
        plan_json = json.dumps(
            {
                "domain": "biology",
                "subtasks": [],
                "search_queries": ["CRISPR gene editing"],
                "completion_criteria": "Explain CRISPR",
            }
        )
        llm = FakeLLM(responses=[plan_json])
        planner = PlannerAgent(llm=llm)

        result = await planner.run(ResearchState(question="What is CRISPR?"))

        assert result["plan"].subtasks == ["What is CRISPR?"]

    async def test_calls_status_callback(self) -> None:
        plan_json = json.dumps(
            {
                "domain": "test",
                "subtasks": ["sub"],
                "search_queries": ["query"],
                "completion_criteria": "done",
            }
        )
        llm = FakeLLM(responses=[plan_json])
        planner = PlannerAgent(llm=llm)
        statuses, state = _make_status_tracker()

        await planner.run(state)

        assert statuses == [ResearchStatus.PLANNING]


# ---------------------------------------------------------------------------
# ResearcherAgent tests
# ---------------------------------------------------------------------------


class TestResearcherAgent:
    async def test_collects_papers(self) -> None:
        fake_provider = FakeSearchProvider("test_prov", [SAMPLE_PAPER])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        researcher = ResearcherAgent(registry=registry)
        result = await researcher.run(
            ResearchState(question="test", search_queries=["deep learning NLP"])
        )

        assert len(result["papers"]) == 1
        assert result["papers"][0].title == "Deep Learning for NLP"

    async def test_deduplicates_papers(self) -> None:
        fake_provider = FakeSearchProvider("test_prov", [SAMPLE_PAPER])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        researcher = ResearcherAgent(registry=registry)
        result = await researcher.run(
            ResearchState(question="test", search_queries=["query one", "query two"])
        )

        assert len(result["papers"]) == 1

    async def test_empty_queries(self) -> None:
        registry = ProviderRegistry(providers=[])
        researcher = ResearcherAgent(registry=registry)

        result = await researcher.run(ResearchState(question="test", search_queries=[]))

        assert result["papers"] == []
        assert result["error"] == "No search queries to execute"

    async def test_ranks_by_abstract_and_citations(self) -> None:
        paper_no_abstract = PaperResult(
            source="test",
            source_id="1",
            title="No Abstract",
            authors=[],
            abstract="",
            url="",
            citation_count=100,
        )
        paper_with_abstract = PaperResult(
            source="test",
            source_id="2",
            title="Has Abstract",
            authors=[],
            abstract="Some abstract",
            url="",
            citation_count=10,
        )
        fake_provider = FakeSearchProvider("prov", [paper_no_abstract, paper_with_abstract])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        researcher = ResearcherAgent(registry=registry)
        result = await researcher.run(ResearchState(question="test", search_queries=["query"]))

        assert result["papers"][0].title == "Has Abstract"

    async def test_calls_status_callback(self) -> None:
        registry = ProviderRegistry(providers=[])
        researcher = ResearcherAgent(registry=registry)
        statuses, state = _make_status_tracker()
        state["search_queries"] = ["query"]

        await researcher.run(state)

        assert statuses == [ResearchStatus.RESEARCHING]


# ---------------------------------------------------------------------------
# SynthesizerAgent tests
# ---------------------------------------------------------------------------


class TestSynthesizerAgent:
    async def test_produces_synthesis(self) -> None:
        llm = FakeLLM(responses=["Here is a summary of the findings."])
        synthesizer = SynthesizerAgent(llm=llm)

        result = await synthesizer.run(ResearchState(question="test", papers=[SAMPLE_PAPER]))

        assert "summary" in result["synthesis"]
        assert len(llm.calls) == 1

    async def test_no_papers_message(self) -> None:
        llm = FakeLLM(responses=[])
        synthesizer = SynthesizerAgent(llm=llm)

        result = await synthesizer.run(ResearchState(question="test", papers=[]))

        assert "No papers" in result["synthesis"]
        assert len(llm.calls) == 0

    async def test_includes_plan_context(self) -> None:
        plan = ResearchPlan(
            domain="machine learning",
            subtasks=["sub1", "sub2"],
            search_queries=["q1"],
            completion_criteria="thorough answer",
        )
        llm = FakeLLM(responses=["Synthesized with plan context."])
        synthesizer = SynthesizerAgent(llm=llm)

        await synthesizer.run(ResearchState(question="test", papers=[SAMPLE_PAPER], plan=plan))

        prompt_text = llm.calls[0][0].content
        assert "machine learning" in prompt_text
        assert "sub1" in prompt_text
        assert "thorough answer" in prompt_text

    async def test_calls_status_callback(self) -> None:
        llm = FakeLLM(responses=["Summary."])
        synthesizer = SynthesizerAgent(llm=llm)
        statuses, state = _make_status_tracker()
        state["papers"] = [SAMPLE_PAPER]

        await synthesizer.run(state)

        assert statuses == [ResearchStatus.SYNTHESIZING]


# ---------------------------------------------------------------------------
# Format papers helper tests
# ---------------------------------------------------------------------------


class TestFormatPapers:
    def test_formats_paper(self) -> None:
        text = _format_papers([SAMPLE_PAPER])
        assert "Deep Learning for NLP" in text
        assert "Alice Smith" in text
        assert "42" in text

    def test_truncates_long_abstract(self) -> None:
        paper = PaperResult(
            source="test",
            source_id="456",
            title="Long Abstract Paper",
            authors=[],
            abstract="x" * 500,
            url="https://example.com",
        )
        text = _format_papers([paper])
        assert "..." in text

    def test_respects_max_papers(self) -> None:
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
        text = _format_papers(papers, max_papers=5)
        assert "Paper 0" in text
        assert "Paper 4" in text
        assert "Paper 5" not in text


# ---------------------------------------------------------------------------
# Graph tests
# ---------------------------------------------------------------------------


class TestBuildResearchGraph:
    def test_graph_compiles(self) -> None:
        llm = FakeLLM(responses=[])
        registry = ProviderRegistry(providers=[])
        graph = build_research_graph(llm, registry)
        compiled = graph.compile()
        assert compiled is not None

    async def test_full_graph_execution(self) -> None:
        plan_json = json.dumps(
            {
                "domain": "NLP",
                "subtasks": ["How does deep learning help NLP?"],
                "search_queries": ["deep learning NLP"],
                "completion_criteria": "Explain with citations",
            }
        )
        llm = FakeLLM(responses=[plan_json, "Summary: Deep learning is transforming NLP."])
        fake_provider = FakeSearchProvider("test_prov", [SAMPLE_PAPER])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        graph = build_research_graph(llm, registry)
        compiled = graph.compile()
        result = await compiled.ainvoke({"question": "How does deep learning help NLP?"})

        assert result["search_queries"] == ["deep learning NLP"]
        assert len(result["papers"]) == 1
        assert "Deep learning" in result["synthesis"]

    async def test_graph_with_status_callback(self) -> None:
        plan_json = json.dumps(
            {
                "domain": "test",
                "subtasks": ["sub"],
                "search_queries": ["query"],
                "completion_criteria": "done",
            }
        )
        llm = FakeLLM(responses=[plan_json, "Synthesis complete."])
        registry = ProviderRegistry(providers=[])

        graph = build_research_graph(llm, registry)
        compiled = graph.compile()

        statuses: list[ResearchStatus] = []

        def _track(status: ResearchStatus) -> None:
            statuses.append(status)

        await compiled.ainvoke({"question": "test", "status_callback": _track})

        assert ResearchStatus.PLANNING in statuses
        assert ResearchStatus.RESEARCHING in statuses
        assert ResearchStatus.SYNTHESIZING in statuses
