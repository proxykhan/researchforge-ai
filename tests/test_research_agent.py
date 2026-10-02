"""Tests for the multi-agent research graph."""

from __future__ import annotations

import json

from researchforge.agents.critic import CriticAgent
from researchforge.agents.debate import DebateAgent
from researchforge.agents.evaluator import EvaluationAgent, _parse_evaluation
from researchforge.agents.fact_checker import FactCheckerAgent
from researchforge.agents.planner import PlannerAgent
from researchforge.agents.research import build_research_graph
from researchforge.agents.researcher import ResearcherAgent, clean_query
from researchforge.agents.state import (
    CriticResult,
    DebateResult,
    EvaluationResult,
    ResearchPlan,
    ResearchState,
)
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

    async def _track(status: ResearchStatus) -> None:
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

    def test_clean_query_strips_search_syntax(self) -> None:
        assert (
            clean_query('"hantavirus" AND favipiravir OR (monoclonal antibody) 2022..2024')
            == "hantavirus favipiravir monoclonal antibody"
        )
        non_breaking_hyphen = chr(0x2011)
        assert clean_query(f"rack power for 2023{non_breaking_hyphen}2024 supercomputers") == (
            "rack power for supercomputers"
        )
        assert clean_query("sleep and memory") == "sleep and memory"

    async def test_deduplicates_same_paper_across_providers(self) -> None:
        copy = PaperResult(
            source="other",
            source_id="xyz",
            title="Deep learning for NLP.",
            authors=[],
            abstract="",
            url="",
        )
        registry = ProviderRegistry(providers=[])
        registry.register(FakeSearchProvider("a", [SAMPLE_PAPER]))  # type: ignore[arg-type]
        registry.register(FakeSearchProvider("b", [copy]))  # type: ignore[arg-type]

        result = await ResearcherAgent(registry=registry).run(
            ResearchState(question="deep learning", search_queries=["q"])
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

    @staticmethod
    def _two_paper_registry() -> ProviderRegistry:
        relevant = PaperResult(
            source="test",
            source_id="rel",
            title="Sleep deprivation impairs hippocampal memory consolidation",
            authors=[],
            abstract="Human study of sleep loss and memory.",
            url="",
        )
        off_topic = PaperResult(
            source="test",
            source_id="off",
            title="Sleep Deprivation in the Forward-Forward Algorithm",
            authors=[],
            abstract="A neural network training method.",
            url="",
            citation_count=500,
        )
        registry = ProviderRegistry(providers=[])
        registry.register(FakeSearchProvider("prov", [off_topic, relevant]))  # type: ignore[arg-type]
        return registry

    async def test_llm_screen_drops_off_topic_papers(self) -> None:
        llm = FakeLLM(responses=[json.dumps({"relevant": [1]})])
        researcher = ResearcherAgent(registry=self._two_paper_registry(), llm=llm)

        result = await researcher.run(
            ResearchState(
                question="How does sleep deprivation affect memory consolidation?",
                search_queries=["sleep deprivation memory"],
            )
        )

        assert [p.source_id for p in result["papers"]] == ["rel"]
        assert "[1] Sleep deprivation impairs" in llm.calls[0][0].content

    async def test_llm_screen_can_reject_everything(self) -> None:
        llm = FakeLLM(responses=[json.dumps({"relevant": []})])
        researcher = ResearcherAgent(registry=self._two_paper_registry(), llm=llm)

        result = await researcher.run(
            ResearchState(question="protein folding", search_queries=["protein folding"])
        )

        assert result["papers"] == []

    async def test_unparseable_screen_falls_back_to_keyword_ranking(self) -> None:
        llm = FakeLLM(responses=["I think paper one looks good"])
        researcher = ResearcherAgent(registry=self._two_paper_registry(), llm=llm)

        result = await researcher.run(
            ResearchState(
                question="sleep deprivation memory consolidation",
                search_queries=["sleep deprivation memory"],
            )
        )

        assert result["papers"][0].source_id == "rel"
        assert len(result["papers"]) == 2

    async def test_rerun_only_searches_new_queries_and_keeps_papers(self) -> None:
        registry = ProviderRegistry(providers=[])
        provider = FakeSearchProvider("prov", [SAMPLE_PAPER])
        searched: list[str] = []
        original_search = provider.search

        async def tracking_search(query: SearchQuery) -> SearchResponse:
            searched.append(query.query)
            return await original_search(query)

        provider.search = tracking_search  # type: ignore[method-assign]
        registry.register(provider)  # type: ignore[arg-type]
        kept = PaperResult(
            source="earlier", source_id="1", title="Earlier paper", authors=[], abstract="", url=""
        )
        researcher = ResearcherAgent(registry=registry)

        result = await researcher.run(
            ResearchState(
                question="deep learning",
                search_queries=["old query", "new query"],
                searched_queries=["old query"],
                papers=[kept],
            )
        )

        assert searched == ["new query"]
        assert result["papers"][0] is kept
        assert result["searched_queries"] == ["new query", "old query"]


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


def _make_full_graph_responses() -> list[str]:
    """Build the 7 LLM responses for a full graph run, in call order."""
    plan = json.dumps(
        {
            "domain": "NLP",
            "subtasks": ["How does deep learning help NLP?"],
            "search_queries": ["deep learning NLP"],
            "completion_criteria": "Explain with citations",
        }
    )
    synthesis = "Deep learning is transforming NLP via attention mechanisms."
    fact_check = json.dumps(
        [
            {
                "claim": "Deep learning is transforming NLP",
                "status": "supported",
                "confidence": 0.9,
                "evidence": ["Deep Learning for NLP"],
                "reasoning": "Directly stated in the paper.",
            }
        ]
    )
    screen = json.dumps({"relevant": [1]})
    debate = _debate_json(
        judgment="Support has stronger evidence.",
        conclusion="Deep learning significantly advances NLP.",
    )
    critic = json.dumps(
        {
            "completeness_score": 0.85,
            "missing_areas": [],
            "weak_points": [],
            "needs_more_research": False,
            "additional_queries": [],
            "feedback": "Research is adequate.",
        }
    )
    evaluation = json.dumps(
        {
            "retrieval_score": 0.8,
            "citation_score": 0.7,
            "factual_grounding_score": 0.85,
            "relevance_score": 0.9,
            "completeness_score": 0.75,
            "overall_score": 0.8,
            "strengths": ["Good coverage", "Well-cited"],
            "weaknesses": ["Could explore more angles"],
            "summary": "Solid research with good evidence base.",
        }
    )
    return [plan, screen, synthesis, fact_check, debate, critic, evaluation]


# ---------------------------------------------------------------------------
# Fact-checker tests
# ---------------------------------------------------------------------------


class TestFactCheckerAgent:
    async def test_parses_valid_verifications(self) -> None:
        response = json.dumps(
            [
                {
                    "claim": "Transformers are effective",
                    "status": "supported",
                    "confidence": 0.9,
                    "evidence": ["Paper A"],
                    "reasoning": "Direct evidence.",
                }
            ]
        )
        llm = FakeLLM(responses=[response])
        agent = FactCheckerAgent(llm=llm)

        result = await agent.run(
            ResearchState(
                question="test",
                synthesis="Transformers are effective.",
                papers=[SAMPLE_PAPER],
            )
        )

        assert len(result["claim_verifications"]) == 1
        v = result["claim_verifications"][0]
        assert v.status == "supported"
        assert v.confidence == 0.9

    async def test_handles_invalid_json(self) -> None:
        llm = FakeLLM(responses=["not valid json"])
        agent = FactCheckerAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="test", synthesis="Some claim.", papers=[SAMPLE_PAPER])
        )

        assert result["claim_verifications"] == []

    async def test_empty_synthesis(self) -> None:
        llm = FakeLLM(responses=[])
        agent = FactCheckerAgent(llm=llm)

        result = await agent.run(ResearchState(question="test", synthesis="", papers=[]))

        assert result["claim_verifications"] == []
        assert len(llm.calls) == 0

    async def test_clamps_confidence(self) -> None:
        response = json.dumps([{"claim": "test", "status": "supported", "confidence": 5.0}])
        llm = FakeLLM(responses=[response])
        agent = FactCheckerAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="test", synthesis="test", papers=[SAMPLE_PAPER])
        )

        assert result["claim_verifications"][0].confidence == 1.0

    async def test_normalizes_invalid_status(self) -> None:
        response = json.dumps([{"claim": "test", "status": "maybe"}])
        llm = FakeLLM(responses=[response])
        agent = FactCheckerAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="test", synthesis="test", papers=[SAMPLE_PAPER])
        )

        assert result["claim_verifications"][0].status == "insufficient_evidence"

    async def test_calls_status_callback(self) -> None:
        response = json.dumps([])
        llm = FakeLLM(responses=[response])
        agent = FactCheckerAgent(llm=llm)
        statuses, state = _make_status_tracker()
        state["synthesis"] = "some text"
        state["papers"] = [SAMPLE_PAPER]

        await agent.run(state)

        assert statuses == [ResearchStatus.VERIFYING]


# ---------------------------------------------------------------------------
# Debate tests
# ---------------------------------------------------------------------------


def _debate_json(**overrides: str) -> str:
    data = {
        "support_argument": "Support argument.",
        "skeptic_argument": "Skeptic argument.",
        "judgment": "Support wins.",
        "conclusion": "Conclusion here.",
    }
    data.update(overrides)
    return json.dumps(data)


class TestDebateAgent:
    async def test_produces_debate_result(self) -> None:
        llm = FakeLLM(responses=[_debate_json()])
        agent = DebateAgent(llm=llm)

        result = await agent.run(
            ResearchState(
                question="Is deep learning effective?",
                synthesis="DL is effective.",
                papers=[SAMPLE_PAPER],
            )
        )

        debate = result["debate_result"]
        assert isinstance(debate, DebateResult)
        assert debate.support_argument == "Support argument."
        assert debate.skeptic_argument == "Skeptic argument."
        assert debate.judgment == "Support wins."
        assert debate.conclusion == "Conclusion here."

    async def test_single_llm_call(self) -> None:
        llm = FakeLLM(responses=[_debate_json()])
        agent = DebateAgent(llm=llm)

        await agent.run(ResearchState(question="q", synthesis="text", papers=[SAMPLE_PAPER]))

        assert len(llm.calls) == 1

    async def test_parses_json_wrapped_in_prose(self) -> None:
        llm = FakeLLM(responses=[f"Here is the debate:\n```json\n{_debate_json()}\n```"])
        agent = DebateAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="q", synthesis="text", papers=[SAMPLE_PAPER])
        )

        assert result["debate_result"].judgment == "Support wins."

    async def test_empty_synthesis(self) -> None:
        llm = FakeLLM(responses=[])
        agent = DebateAgent(llm=llm)

        result = await agent.run(ResearchState(question="q", synthesis=""))

        debate = result["debate_result"]
        assert "No synthesis" in debate.support_argument
        assert len(llm.calls) == 0

    async def test_handles_invalid_json(self) -> None:
        llm = FakeLLM(responses=["not json"])
        agent = DebateAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="q", synthesis="text", papers=[SAMPLE_PAPER])
        )

        debate = result["debate_result"]
        assert debate.judgment == "not json"

    async def test_calls_status_callback(self) -> None:
        llm = FakeLLM(responses=[_debate_json()])
        agent = DebateAgent(llm=llm)
        statuses, state = _make_status_tracker()
        state["synthesis"] = "text"
        state["papers"] = [SAMPLE_PAPER]

        await agent.run(state)

        assert statuses == [ResearchStatus.DEBATING]


# ---------------------------------------------------------------------------
# Critic tests
# ---------------------------------------------------------------------------


class TestCriticAgent:
    async def test_parses_valid_result(self) -> None:
        response = json.dumps(
            {
                "completeness_score": 0.8,
                "missing_areas": ["area1"],
                "weak_points": ["weak1"],
                "needs_more_research": False,
                "additional_queries": [],
                "feedback": "Good research.",
            }
        )
        llm = FakeLLM(responses=[response])
        agent = CriticAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="q", synthesis="text", papers=[SAMPLE_PAPER])
        )

        cr = result["critic_result"]
        assert isinstance(cr, CriticResult)
        assert cr.completeness_score == 0.8
        assert cr.missing_areas == ["area1"]
        assert not cr.needs_more_research
        assert result["iteration"] == 1

    async def test_requests_more_research(self) -> None:
        response = json.dumps(
            {
                "completeness_score": 0.3,
                "missing_areas": ["gap"],
                "weak_points": [],
                "needs_more_research": True,
                "additional_queries": ["new query"],
                "feedback": "More needed.",
            }
        )
        llm = FakeLLM(responses=[response])
        agent = CriticAgent(llm=llm, max_iterations=3)

        result = await agent.run(
            ResearchState(question="q", synthesis="text", papers=[SAMPLE_PAPER], iteration=0)
        )

        cr = result["critic_result"]
        assert cr.needs_more_research is True
        assert cr.additional_queries == ["new query"]
        assert "new query" in result["search_queries"]

    async def test_no_rerun_when_score_is_adequate(self) -> None:
        response = json.dumps(
            {
                "completeness_score": 0.75,
                "needs_more_research": True,
                "additional_queries": ["more"],
                "feedback": "Minor gaps.",
            }
        )
        llm = FakeLLM(responses=[response])
        agent = CriticAgent(llm=llm, max_iterations=3)

        result = await agent.run(
            ResearchState(question="q", synthesis="text", papers=[], iteration=0)
        )

        assert result["critic_result"].needs_more_research is False

    async def test_enforces_max_iterations(self) -> None:
        response = json.dumps(
            {
                "completeness_score": 0.3,
                "needs_more_research": True,
                "additional_queries": ["more"],
                "feedback": "Needs more.",
            }
        )
        llm = FakeLLM(responses=[response])
        agent = CriticAgent(llm=llm, max_iterations=2)

        result = await agent.run(
            ResearchState(question="q", synthesis="text", papers=[], iteration=1)
        )

        cr = result["critic_result"]
        assert cr.needs_more_research is False

    async def test_handles_invalid_json(self) -> None:
        llm = FakeLLM(responses=["not json"])
        agent = CriticAgent(llm=llm)

        result = await agent.run(ResearchState(question="q", synthesis="text", papers=[]))

        cr = result["critic_result"]
        assert cr.completeness_score == 0.5
        assert not cr.needs_more_research

    async def test_calls_status_callback(self) -> None:
        response = json.dumps(
            {"completeness_score": 0.9, "needs_more_research": False, "feedback": "ok"}
        )
        llm = FakeLLM(responses=[response])
        agent = CriticAgent(llm=llm)
        statuses, state = _make_status_tracker()
        state["synthesis"] = "text"

        await agent.run(state)

        assert statuses == [ResearchStatus.CRITIQUING]


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------


class TestEvaluationAgent:
    async def test_parses_valid_scores(self) -> None:
        response = json.dumps(
            {
                "retrieval_score": 0.8,
                "citation_score": 0.7,
                "factual_grounding_score": 0.85,
                "relevance_score": 0.9,
                "completeness_score": 0.75,
                "overall_score": 0.8,
                "strengths": ["Good coverage"],
                "weaknesses": ["Missing angles"],
                "summary": "Solid work.",
            }
        )
        llm = FakeLLM(responses=[response])
        agent = EvaluationAgent(llm=llm)

        result = await agent.run(
            ResearchState(
                question="test",
                synthesis="Some synthesis.",
                papers=[SAMPLE_PAPER],
            )
        )

        ev = result["evaluation"]
        assert isinstance(ev, EvaluationResult)
        assert ev.retrieval_score == 0.8
        assert ev.overall_score == 0.8
        assert ev.strengths == ["Good coverage"]
        assert ev.weaknesses == ["Missing angles"]

    async def test_empty_synthesis(self) -> None:
        llm = FakeLLM(responses=[])
        agent = EvaluationAgent(llm=llm)

        result = await agent.run(ResearchState(question="test", synthesis=""))

        ev = result["evaluation"]
        assert ev.overall_score == 0.0
        assert "No synthesis" in ev.summary
        assert len(llm.calls) == 0

    async def test_handles_invalid_json(self) -> None:
        llm = FakeLLM(responses=["not valid json"])
        agent = EvaluationAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="test", synthesis="text", papers=[SAMPLE_PAPER])
        )

        ev = result["evaluation"]
        assert ev.overall_score == 0.5
        assert "Unable to parse" in ev.summary

    async def test_clamps_scores(self) -> None:
        response = json.dumps(
            {
                "retrieval_score": 5.0,
                "citation_score": -1.0,
                "factual_grounding_score": 0.5,
                "relevance_score": 0.5,
                "completeness_score": 0.5,
                "overall_score": 0.5,
            }
        )
        llm = FakeLLM(responses=[response])
        agent = EvaluationAgent(llm=llm)

        result = await agent.run(
            ResearchState(question="test", synthesis="text", papers=[SAMPLE_PAPER])
        )

        ev = result["evaluation"]
        assert ev.retrieval_score == 1.0
        assert ev.citation_score == 0.0

    async def test_calls_status_callback(self) -> None:
        response = json.dumps(
            {
                "retrieval_score": 0.5,
                "citation_score": 0.5,
                "factual_grounding_score": 0.5,
                "relevance_score": 0.5,
                "completeness_score": 0.5,
                "overall_score": 0.5,
            }
        )
        llm = FakeLLM(responses=[response])
        agent = EvaluationAgent(llm=llm)
        statuses, state = _make_status_tracker()
        state["synthesis"] = "text"
        state["papers"] = [SAMPLE_PAPER]

        await agent.run(state)

        assert statuses == [ResearchStatus.EVALUATING]


class TestParseEvaluation:
    def test_non_list_strengths(self) -> None:
        data = json.dumps({"strengths": "just a string", "weaknesses": 42})
        result = _parse_evaluation(data)
        assert result.strengths == []
        assert result.weaknesses == []

    def test_non_numeric_scores_default(self) -> None:
        data = json.dumps({"retrieval_score": "high", "overall_score": None})
        result = _parse_evaluation(data)
        assert result.retrieval_score == 0.5
        assert result.overall_score == 0.5


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
        responses = _make_full_graph_responses()
        llm = FakeLLM(responses=responses)
        fake_provider = FakeSearchProvider("test_prov", [SAMPLE_PAPER])
        registry = ProviderRegistry(providers=[])
        registry.register(fake_provider)  # type: ignore[arg-type]

        graph = build_research_graph(llm, registry)
        compiled = graph.compile()
        result = await compiled.ainvoke({"question": "How does deep learning help NLP?"})

        assert len(result["papers"]) == 1
        assert result["synthesis"] is not None
        assert len(result["claim_verifications"]) == 1
        assert result["debate_result"] is not None
        assert result["critic_result"] is not None
        assert result["evaluation"] is not None
        assert isinstance(result["evaluation"], EvaluationResult)
        assert result["evaluation"].overall_score == 0.8

    async def test_graph_with_status_callback(self) -> None:
        responses = _make_full_graph_responses()
        llm = FakeLLM(responses=responses)
        registry = ProviderRegistry(providers=[])

        graph = build_research_graph(llm, registry)
        compiled = graph.compile()

        statuses: list[ResearchStatus] = []

        async def _track(status: ResearchStatus) -> None:
            statuses.append(status)

        await compiled.ainvoke({"question": "test", "status_callback": _track})

        assert ResearchStatus.PLANNING in statuses
        assert ResearchStatus.RESEARCHING in statuses
        assert ResearchStatus.SYNTHESIZING in statuses
        assert ResearchStatus.VERIFYING in statuses
        assert ResearchStatus.DEBATING in statuses
        assert ResearchStatus.CRITIQUING in statuses
        assert ResearchStatus.EVALUATING in statuses
