"""Research agent graph — wires all agents into a LangGraph state graph.

Flow: plan → search → synthesize → verify_and_debate → critic → evaluate
      ↑                                                   │
      └──────── (if critic says more research needed) ────┘

The verify_and_debate node runs fact-checking and debate concurrently
since they are independent — both need only the synthesis and papers.
"""

from __future__ import annotations

import asyncio

from langgraph.graph import END, StateGraph

from researchforge.agents.critic import CriticAgent
from researchforge.agents.debate import DebateAgent
from researchforge.agents.evaluator import EvaluationAgent
from researchforge.agents.fact_checker import FactCheckerAgent
from researchforge.agents.planner import PlannerAgent
from researchforge.agents.researcher import ResearcherAgent
from researchforge.agents.state import ResearchState, StatusCallback
from researchforge.agents.synthesizer import SynthesizerAgent
from researchforge.integrations.registry import ProviderRegistry
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig
from researchforge.observability.instrumentation import traced_agent_node


def _should_continue(state: ResearchState) -> str:
    """Decide whether the critic loop should continue or finish."""
    critic = state.get("critic_result")
    if critic and critic.needs_more_research:
        return "execute_search"
    return "evaluate"


def build_research_graph(
    llm: LLMProvider,
    registry: ProviderRegistry,
    llm_config: LLMConfig | None = None,
) -> StateGraph[ResearchState]:
    """Create the full multi-agent research graph."""
    config = llm_config or LLMConfig()

    planner = PlannerAgent(llm=llm, llm_config=config)
    researcher = ResearcherAgent(registry=registry, llm=llm, llm_config=config)
    synthesizer = SynthesizerAgent(llm=llm, llm_config=config)
    fact_checker = FactCheckerAgent(llm=llm, llm_config=config)
    debater = DebateAgent(llm=llm, llm_config=config)
    critic = CriticAgent(llm=llm, llm_config=config)
    evaluator = EvaluationAgent(llm=llm, llm_config=config)

    async def verify_and_debate(state: ResearchState) -> ResearchState:
        fc_result, db_result = await asyncio.gather(
            fact_checker.run(state),
            debater.run(state),
        )
        merged: ResearchState = {}
        merged.update(fc_result)
        merged.update(db_result)
        return merged

    graph = StateGraph(ResearchState)
    graph.add_node("plan_research", traced_agent_node("planner")(planner.run))
    graph.add_node("execute_search", traced_agent_node("researcher")(researcher.run))
    graph.add_node("synthesize", traced_agent_node("synthesizer")(synthesizer.run))
    graph.add_node(
        "verify_and_debate",
        traced_agent_node("verify_and_debate")(verify_and_debate),
    )
    graph.add_node("critic", traced_agent_node("critic")(critic.run))
    graph.add_node("evaluate", traced_agent_node("evaluator")(evaluator.run))

    graph.set_entry_point("plan_research")
    graph.add_edge("plan_research", "execute_search")
    graph.add_edge("execute_search", "synthesize")
    graph.add_edge("synthesize", "verify_and_debate")
    graph.add_edge("verify_and_debate", "critic")
    graph.add_conditional_edges("critic", _should_continue)
    graph.add_edge("evaluate", END)

    return graph


__all__ = [
    "ResearchState",
    "StatusCallback",
    "build_research_graph",
]
