"""Evaluation agent — scores the research output across quality dimensions."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from researchforge.agents.state import EvaluationResult, ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)

EVALUATOR_SYSTEM = """\
You are a research evaluation agent. Score the quality of a completed research \
effort across these dimensions (each 0.0 to 1.0):

1. retrieval_score: Did the search find relevant, high-quality papers?
2. citation_score: Are claims properly cited? Are citations traceable?
3. factual_grounding_score: Are conclusions grounded in evidence, not speculation?
4. relevance_score: Does the output actually answer the research question?
5. completeness_score: Are all aspects of the question addressed?

Also provide:
- overall_score: weighted average reflecting overall quality
- strengths: list of what was done well
- weaknesses: list of areas for improvement
- summary: one-paragraph overall assessment

Return JSON:
{
  "retrieval_score": 0.0-1.0,
  "citation_score": 0.0-1.0,
  "factual_grounding_score": 0.0-1.0,
  "relevance_score": 0.0-1.0,
  "completeness_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1"],
  "summary": "Overall assessment paragraph."
}

Be calibrated: a perfect score means genuinely excellent work across the board. \
Most research will score 0.5-0.8. Return ONLY valid JSON, no other text.\
"""


@dataclass
class EvaluationAgent:
    """Evaluates the final research output across quality dimensions."""

    llm: LLMProvider
    llm_config: LLMConfig = field(default_factory=LLMConfig)

    async def run(self, state: ResearchState) -> ResearchState:
        callback = state.get("status_callback")
        if callback:
            await callback(ResearchStatus.EVALUATING)

        synthesis = state.get("synthesis", "")
        question = state.get("question", "")
        papers = state.get("papers", [])
        verifications = state.get("claim_verifications", [])
        debate = state.get("debate_result")
        critic = state.get("critic_result")

        if not synthesis:
            return {
                "evaluation": EvaluationResult(
                    retrieval_score=0.0,
                    citation_score=0.0,
                    factual_grounding_score=0.0,
                    relevance_score=0.0,
                    completeness_score=0.0,
                    overall_score=0.0,
                    summary="No synthesis produced to evaluate.",
                )
            }

        prompt = self._build_prompt(question, synthesis, papers, verifications, debate, critic)

        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=1024,
            system=EVALUATOR_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=prompt)],
            config=config,
        )

        result = _parse_evaluation(response.content)
        logger.info("Evaluation complete: overall=%.2f", result.overall_score)
        return {"evaluation": result}

    @staticmethod
    def _build_prompt(
        question: str,
        synthesis: str,
        papers: Sequence[object],
        verifications: Sequence[object],
        debate: object | None,
        critic: object | None,
    ) -> str:
        parts = [
            f"Research question: {question}",
            f"Papers found: {len(papers)}",
            f"\nSynthesis:\n{synthesis}",
        ]

        if verifications:
            parts.append(f"\nFact-check results: {len(verifications)} claims verified")

        if debate is not None:
            parts.append("\nDebate was conducted")

        if critic is not None:
            parts.append("\nCritic review was performed")

        return "\n".join(parts)


def _clamp(value: object) -> float:
    if not isinstance(value, (int, float)):
        return 0.5
    return max(0.0, min(1.0, float(value)))


def _parse_evaluation(content: str) -> EvaluationResult:
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")

        strengths = data.get("strengths", [])
        if not isinstance(strengths, list):
            strengths = []

        weaknesses = data.get("weaknesses", [])
        if not isinstance(weaknesses, list):
            weaknesses = []

        return EvaluationResult(
            retrieval_score=_clamp(data.get("retrieval_score", 0.5)),
            citation_score=_clamp(data.get("citation_score", 0.5)),
            factual_grounding_score=_clamp(data.get("factual_grounding_score", 0.5)),
            relevance_score=_clamp(data.get("relevance_score", 0.5)),
            completeness_score=_clamp(data.get("completeness_score", 0.5)),
            overall_score=_clamp(data.get("overall_score", 0.5)),
            strengths=[str(s) for s in strengths],
            weaknesses=[str(w) for w in weaknesses],
            summary=str(data.get("summary", "")),
        )
    except (json.JSONDecodeError, ValueError):
        logger.warning("Evaluator returned invalid JSON, using defaults")
        return EvaluationResult(
            retrieval_score=0.5,
            citation_score=0.5,
            factual_grounding_score=0.5,
            relevance_score=0.5,
            completeness_score=0.5,
            overall_score=0.5,
            summary="Unable to parse evaluation response.",
        )
