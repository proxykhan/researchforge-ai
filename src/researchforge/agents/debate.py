"""Debate agent — runs a support/skeptic/judge debate on the synthesis.

All three roles are produced in one LLM call: the separate calls each resent the
same synthesis and paper context, which on token-per-minute-limited providers
cost more wall-clock time than any parallelism could recover.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from researchforge.agents.state import DebateResult, ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)

DEBATE_SYSTEM = """\
You run a structured academic debate about a research synthesis, using ONLY the \
paper evidence provided. Play three roles in order:

1. SUPPORT: the strongest evidence for the synthesis's main conclusions, citing \
papers by title. If the evidence is weak, say so — do not invent support.
2. SKEPTIC: legitimate limitations, gaps, or counterevidence, citing papers by \
title. Do not manufacture disagreement where the evidence agrees.
3. JUDGE: weigh both sides and state which has stronger evidence, then give a \
balanced conclusion that reflects the weight of evidence.

Never cite a paper that is not in the provided list. Keep each argument to one \
short paragraph.

Return ONLY valid JSON:
{
  "support_argument": "...",
  "skeptic_argument": "...",
  "judgment": "...",
  "conclusion": "..."
}\
"""


@dataclass
class DebateAgent:
    """Runs a support/skeptic/judge debate in a single structured call."""

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
        prompt = "\n\n".join(
            [
                f"Research question: {question}",
                f"Synthesis:\n{synthesis}",
                f"Papers:\n{paper_context}",
            ]
        )

        config = LLMConfig(model=self.llm_config.model, max_tokens=1024, system=DEBATE_SYSTEM)
        response = await self.llm.complete(
            messages=[Message(role="user", content=prompt)],
            config=config,
        )

        result = self._parse(response.content, question)
        logger.info("Debate completed on: %s", question[:80])
        return {"debate_result": result}

    @staticmethod
    def _parse(content: str, question: str) -> DebateResult:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                return DebateResult(
                    topic=question,
                    support_argument=str(data.get("support_argument", "")),
                    skeptic_argument=str(data.get("skeptic_argument", "")),
                    judgment=str(data.get("judgment", "Unable to judge.")),
                    conclusion=str(data.get("conclusion", "No conclusion reached.")),
                )
        logger.warning("Debate returned invalid JSON, using raw response")
        return DebateResult(
            topic=question,
            support_argument="",
            skeptic_argument="",
            judgment=content,
            conclusion=content,
        )
