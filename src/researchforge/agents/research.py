"""Research agent graph — wires all agents into a LangGraph state graph.

Flow: plan → search → synthesize → fact_check → debate → critic
      ↑                                                    │
      └──────── (if critic says more research needed) ─────┘
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from researchforge.agents.critic import CriticAgent
from researchforge.agents.debate import DebateAgent
from researchforge.agents.fact_checker import FactCheckerAgent
from researchforge.agents.planner import PlannerAgent
from researchforge.agents.researcher import ResearcherAgent
from researchforge.agents.state import ResearchState, StatusCallback
from researchforge.agents.synthesizer import SynthesizerAgent
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig


def _should_continue(state: ResearchState) -> str:
    """Decide whether the critic loop should continue or finish."""
    critic = state.get("critic_result")
    if critic and critic.needs_more_research:
        return "execute_search"
    return END


def build_research_graph(
    llm: LLMProvider,
    registry: ProviderRegistry,
    llm_config: LLMConfig | None = None,
) -> StateGraph[ResearchState]:
    """Create the full multi-agent research graph."""
    config = llm_config or LLMConfig()

    planner = PlannerAgent(llm=llm, llm_config=config)
    researcher = ResearcherAgent(registry=registry)
    synthesizer = SynthesizerAgent(llm=llm, llm_config=config)
    fact_checker = FactCheckerAgent(llm=llm, llm_config=config)
    debater = DebateAgent(llm=llm, llm_config=config)
    critic = CriticAgent(llm=llm, llm_config=config)

    graph = StateGraph(ResearchState)
    graph.add_node("plan_research", planner.run)
    graph.add_node("execute_search", researcher.run)
    graph.add_node("synthesize", synthesizer.run)
    graph.add_node("fact_check", fact_checker.run)
    graph.add_node("debate", debater.run)
    graph.add_node("critic", critic.run)

    graph.set_entry_point("plan_research")
    graph.add_edge("plan_research", "execute_search")
    graph.add_edge("execute_search", "synthesize")
    graph.add_edge("synthesize", "fact_check")
    graph.add_edge("fact_check", "debate")
    graph.add_edge("debate", "critic")
    graph.add_conditional_edges("critic", _should_continue)

    return graph


__all__ = [
    "ResearchState",
    "StatusCallback",
    "build_research_graph",
]
