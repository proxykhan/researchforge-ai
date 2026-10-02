"""Critic agent — evaluates research completeness and can request more research."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from researchforge.agents.state import CriticResult, ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 2
# A re-research pass re-runs search, synthesis, verification and debate, so it is
# reserved for clearly inadequate results rather than any gap the critic notices.
RETRY_SCORE_THRESHOLD = 0.6

CRITIC_SYSTEM = """\
You are a research critic agent. Evaluate the completeness and quality of a \
research effort. Consider:

1. Does the synthesis adequately answer the research question?
2. Are there important perspectives or subtopics that were missed?
3. Are any claims weakly supported or contradicted?
4. Are there gaps in the evidence that could be filled with more research?

Return JSON:
{
  "completeness_score": 0.0 to 1.0,
  "missing_areas": ["area 1", "area 2"],
  "weak_points": ["weakness 1"],
  "needs_more_research": true or false,
  "additional_queries": ["query 1", "query 2"],
  "feedback": "overall assessment"
}

Guidelines:
- Only set needs_more_research to true if critical gaps exist.
- additional_queries should be specific search queries to fill identified gaps.
- Be constructive, not adversarial.
- A completeness_score above 0.7 means the research is adequate.
- Return ONLY valid JSON, no other text.\
"""


@dataclass
class CriticAgent:
    """Evaluates research quality and can trigger additional research."""

    llm: LLMProvider
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    max_iterations: int = MAX_ITERATIONS

    async def run(self, state: ResearchState) -> ResearchState:
        callback = state.get("status_callback")
        if callback:
            await callback(ResearchStatus.CRITIQUING)

        iteration = state.get("iteration", 0)
        synthesis = state.get("synthesis", "")
        question = state.get("question", "")
        papers = state.get("papers", [])
        verifications = state.get("claim_verifications", [])
        debate = state.get("debate_result")

        context_parts = [
            f"Research question: {question}",
            f"Current iteration: {iteration + 1}",
            f"Papers found: {len(papers)}",
            f"\nSynthesis:\n{synthesis}",
        ]

        if verifications:
            supported = sum(1 for v in verifications if v.status == "supported")
            total = len(verifications)
            context_parts.append(f"\nFact-check: {supported}/{total} claims supported")

        if debate:
            context_parts.append(f"\nDebate conclusion:\n{debate.conclusion}")

        prompt = "\n".join(context_parts)

        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=1024,
            system=CRITIC_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=prompt)],
            config=config,
        )

        result = self._parse_result(response.content, iteration)
        logger.info(
            "Critic: score=%.2f, needs_more=%s, iteration=%d/%d",
            result.completeness_score,
            result.needs_more_research,
            iteration + 1,
            self.max_iterations,
        )

        updates: ResearchState = {
            "critic_result": result,
            "iteration": iteration + 1,
        }

        if result.needs_more_research and result.additional_queries:
            existing = state.get("search_queries", [])
            updates["search_queries"] = existing + result.additional_queries

        return updates

    def _parse_result(self, content: str, iteration: int) -> CriticResult:
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")

            score = data.get("completeness_score", 0.5)
            if not isinstance(score, (int, float)):
                score = 0.5
            score = max(0.0, min(1.0, float(score)))

            missing = data.get("missing_areas", [])
            if not isinstance(missing, list):
                missing = []

            weak = data.get("weak_points", [])
            if not isinstance(weak, list):
                weak = []

            needs_more = bool(data.get("needs_more_research", False))
            if iteration + 1 >= self.max_iterations or score >= RETRY_SCORE_THRESHOLD:
                needs_more = False

            queries = data.get("additional_queries", [])
            if not isinstance(queries, list):
                queries = []

            return CriticResult(
                completeness_score=score,
                missing_areas=[str(m) for m in missing],
                weak_points=[str(w) for w in weak],
                needs_more_research=needs_more,
                additional_queries=[str(q) for q in queries] if needs_more else [],
                feedback=str(data.get("feedback", "")),
            )
        except (json.JSONDecodeError, ValueError):
            logger.warning("Critic returned invalid JSON, using defaults")
            return CriticResult(
                completeness_score=0.5,
                needs_more_research=False,
                feedback="Unable to parse critic response.",
            )
