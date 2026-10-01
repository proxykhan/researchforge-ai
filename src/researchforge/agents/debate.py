"""Debate agent — runs a support/skeptic/judge debate on the synthesis."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from researchforge.agents.state import DebateResult, ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)

SUPPORT_SYSTEM = """\
You are a support agent in an academic debate. Given a research synthesis and \
paper evidence, find the strongest evidence SUPPORTING the main conclusions.

Be evidence-driven: cite specific papers and findings. Do not invent evidence. \
If the evidence is genuinely strong, say so. If it is weak, acknowledge that \
honestly — do not fabricate support.

Respond with a concise argument (2-4 paragraphs) citing papers by title.\
"""

SKEPTIC_SYSTEM = """\
You are a skeptic agent in an academic debate. Given a research synthesis and \
paper evidence, find legitimate challenges, limitations, and counterevidence \
to the main conclusions.

Be evidence-driven: cite specific papers and findings. Do not create artificial \
disagreement where evidence is not actually contradictory. If the conclusions \
are well-supported, say so honestly — do not fabricate objections.

Respond with a concise critique (2-4 paragraphs) citing papers by title.\
"""

JUDGE_SYSTEM = """\
You are a judge evaluating an academic debate. Given the support and skeptic \
arguments, weigh the evidence and reach a balanced conclusion.

Return JSON:
{
  "judgment": "your evaluation of which side has stronger evidence",
  "conclusion": "the balanced conclusion incorporating both perspectives"
}

Be fair. Acknowledge strengths on both sides. The conclusion should reflect \
the weight of evidence, not simply split the difference.

Return ONLY valid JSON, no other text.\
"""


@dataclass
class DebateAgent:
    """Runs a three-phase debate: support, skeptic, judge."""

    llm: LLMProvider
    llm_config: LLMConfig = field(default_factory=LLMConfig)

    async def run(self, state: ResearchState) -> ResearchState:
        synthesis = state.get("synthesis", "")
        papers = state.get("papers", [])
        question = state.get("question", "")
        callback = state.get("status_callback")
        if callback:
            await callback(ResearchStatus.DEBATING)

        if not synthesis:
            return {
                "debate_result": DebateResult(
                    topic=question,
                    support_argument="No synthesis to debate.",
                    skeptic_argument="No synthesis to debate.",
                    judgment="No debate conducted.",
                    conclusion="Insufficient material for debate.",
                )
            }

        paper_context = "\n".join(
            f"- {p.title}: {p.abstract[:200]}" for p in papers[:10] if p.abstract
        )
        parts = [
            f"Research question: {question}",
            f"Synthesis:\n{synthesis}",
            f"Papers:\n{paper_context}",
        ]
        context = "\n\n".join(parts)

        support, skeptic = await asyncio.gather(
            self._run_side(context, SUPPORT_SYSTEM),
            self._run_side(context, SKEPTIC_SYSTEM),
        )
        judgment, conclusion = await self._run_judge(context, support, skeptic)

        result = DebateResult(
            topic=question,
            support_argument=support,
            skeptic_argument=skeptic,
            judgment=judgment,
            conclusion=conclusion,
        )
        logger.info("Debate completed on: %s", question[:80])
        return {"debate_result": result}

    async def _run_side(self, context: str, system: str) -> str:
        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=1024,
            system=system,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=context)],
            config=config,
        )
        return response.content

    async def _run_judge(self, context: str, support: str, skeptic: str) -> tuple[str, str]:
        judge_prompt = f"{context}\n\nSUPPORT ARGUMENT:\n{support}\n\nSKEPTIC ARGUMENT:\n{skeptic}"
        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=1024,
            system=JUDGE_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=judge_prompt)],
            config=config,
        )
        return self._parse_judgment(response.content)

    @staticmethod
    def _parse_judgment(content: str) -> tuple[str, str]:
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return (
                    str(data.get("judgment", "Unable to judge.")),
                    str(data.get("conclusion", "No conclusion reached.")),
                )
        except (json.JSONDecodeError, ValueError):
            logger.warning("Judge returned invalid JSON, using raw response")
        return (content, content)
