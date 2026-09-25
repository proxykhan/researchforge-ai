"""Fact-checker agent — verifies claims in the synthesis against evidence."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from researchforge.agents.state import ClaimVerification, ResearchState
from researchforge.api.schemas import ResearchStatus
from researchforge.llm.base import LLMProvider
from researchforge.llm.models import LLMConfig, Message

logger = logging.getLogger(__name__)

FACT_CHECK_SYSTEM = """\
You are a fact-checking agent. Given a research synthesis and a list of paper \
abstracts, identify the key factual claims in the synthesis and verify each \
against the available evidence.

Return a JSON array of claim verifications:
[
  {
    "claim": "the specific claim being checked",
    "status": "supported|unsupported|contradicted|insufficient_evidence",
    "confidence": 0.0 to 1.0,
    "evidence": ["paper title or quote that supports/contradicts"],
    "reasoning": "brief explanation of your verdict"
  }
]

Rules:
- Only check factual claims, not opinions or framing.
- "supported" means direct evidence exists in the papers.
- "contradicted" means evidence directly conflicts with the claim.
- "unsupported" means the claim is made but no evidence backs it.
- "insufficient_evidence" means the topic is mentioned but evidence is unclear.
- Confidence should reflect how strong the evidence is.
- Return ONLY valid JSON, no other text.\
"""


@dataclass
class FactCheckerAgent:
    """Verifies claims in the synthesis against paper evidence."""

    llm: LLMProvider
    llm_config: LLMConfig = field(default_factory=LLMConfig)

    async def run(self, state: ResearchState) -> ResearchState:
        synthesis = state.get("synthesis", "")
        papers = state.get("papers", [])
        callback = state.get("status_callback")
        if callback:
            callback(ResearchStatus.VERIFYING)

        if not synthesis or not papers:
            return {"claim_verifications": []}

        paper_context = "\n\n".join(
            f"- {p.title}: {p.abstract[:300]}" for p in papers[:15] if p.abstract
        )
        prompt = (
            f"Synthesis to fact-check:\n{synthesis}\n\nAvailable paper evidence:\n{paper_context}"
        )

        config = LLMConfig(
            model=self.llm_config.model,
            max_tokens=2048,
            system=FACT_CHECK_SYSTEM,
        )
        response = await self.llm.complete(
            messages=[Message(role="user", content=prompt)],
            config=config,
        )

        verifications = self._parse_verifications(response.content)
        logger.info("Fact-checker verified %d claims", len(verifications))
        return {"claim_verifications": verifications}

    @staticmethod
    def _parse_verifications(content: str) -> list[ClaimVerification]:
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                return []

            results: list[ClaimVerification] = []
            for item in data:
                if not isinstance(item, dict) or "claim" not in item:
                    continue
                status = str(item.get("status", "insufficient_evidence"))
                if status not in (
                    "supported",
                    "unsupported",
                    "contradicted",
                    "insufficient_evidence",
                ):
                    status = "insufficient_evidence"

                confidence = item.get("confidence", 0.5)
                if not isinstance(confidence, (int, float)):
                    confidence = 0.5
                confidence = max(0.0, min(1.0, float(confidence)))

                evidence = item.get("evidence", [])
                if not isinstance(evidence, list):
                    evidence = []

                results.append(
                    ClaimVerification(
                        claim=str(item["claim"]),
                        status=status,
                        confidence=confidence,
                        evidence=[str(e) for e in evidence],
                        reasoning=str(item.get("reasoning", "")),
                    )
                )
            return results
        except (json.JSONDecodeError, ValueError):
            logger.warning("Fact-checker returned invalid JSON")
            return []
