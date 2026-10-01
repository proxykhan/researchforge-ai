"""Planner agent — decomposes a research question into a structured plan."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from researchforge.agents.state import ResearchPlan, ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """\
You are a research planning agent. Given a research question, produce a \
structured research plan as JSON with these fields:

{
  "domain": "the research domain (e.g. 'machine learning', 'neuroscience')",
  "subtasks": ["2-4 focused sub-questions that together answer the main question"],
  "search_queries": ["2-4 search queries optimized for academic search engines"],
  "completion_criteria": "a sentence describing what a good answer looks like"
}

Return ONLY valid JSON, no other text.\
"""


@dataclass
class PlannerAgent:
    """Decomposes a research question into subtasks and search queries."""

    llm: LLMProvider
    llm_config: LLMConfig = field(default_factory=LLMConfig)

    async def run(self, state: ResearchState) -> ResearchState:
        question = state["question"]
        callback = state.get("status_callback")
        if callback:
            await callback(ResearchStatus.PLANNING)

        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=1024,
            system=PLANNER_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=question)],
            config=config,
        )

        plan = self._parse_plan(response.content, question)
        return {"plan": plan, "search_queries": plan.search_queries}

    @staticmethod
    def _parse_plan(content: str, fallback_question: str) -> ResearchPlan:
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")

            subtasks = data.get("subtasks", [])
            queries = data.get("search_queries", [])

            if not isinstance(subtasks, list) or not subtasks:
                subtasks = [fallback_question]
            if not isinstance(queries, list) or not queries:
                queries = [fallback_question]

            return ResearchPlan(
                domain=str(data.get("domain", "general")),
                subtasks=[str(s) for s in subtasks],
                search_queries=[str(q) for q in queries],
                completion_criteria=str(data.get("completion_criteria", "")),
            )
        except (json.JSONDecodeError, ValueError):
            logger.warning("Planner returned invalid JSON, using fallback plan")
            return ResearchPlan(
                domain="general",
                subtasks=[fallback_question],
                search_queries=[fallback_question],
                completion_criteria="Answer the research question with cited sources.",
            )
