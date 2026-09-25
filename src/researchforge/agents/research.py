"""Research agent graph — wires Planner, Researcher, and Synthesizer together.

The graph runs: plan → search → synthesize, with status callbacks so the
service layer can report progress to the API.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from researchforge.agents.planner import PlannerAgent
from researchforge.agents.researcher import ResearcherAgent
from researchforge.agents.state import ResearchState, StatusCallback
from researchforge.agents.synthesizer import SynthesizerAgent
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig


def build_research_graph(
    llm: LLMProvider,
    registry: ProviderRegistry,
    llm_config: LLMConfig | None = None,
) -> StateGraph[ResearchState]:
    """Create the three-agent research graph."""
    config = llm_config or LLMConfig()

    planner = PlannerAgent(llm=llm, llm_config=config)
    researcher = ResearcherAgent(registry=registry)
    synthesizer = SynthesizerAgent(llm=llm, llm_config=config)

    graph = StateGraph(ResearchState)
    graph.add_node("plan_research", planner.run)
    graph.add_node("execute_search", researcher.run)
    graph.add_node("synthesize", synthesizer.run)

    graph.set_entry_point("plan_research")
    graph.add_edge("plan_research", "execute_search")
    graph.add_edge("execute_search", "synthesize")
    graph.add_edge("synthesize", END)

    return graph


__all__ = [
    "ResearchState",
    "StatusCallback",
    "build_research_graph",
]
