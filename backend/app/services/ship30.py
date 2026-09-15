"""Ship 30 for 30 grounded writing skill."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.providers.base import ChatProvider, ProviderError


@dataclass(frozen=True)
class Ship30Request:
    topic: str
    grounded_answer: str
    evidence: str


SHIP30_SYSTEM_PROMPT = """
You are the Ship 30 for 30 writing skill inside the Lenny Growth Assistant.

Your job is to transform ONLY the supplied transcript evidence into a
useful approximately 1,250-word essay.

CORE PRINCIPLE:
The transcript evidence is the complete knowledge boundary. You have no
permission to use outside knowledge.

WRITING REQUIREMENTS:
- Write approximately 1,250 words.
- Start with a strong, specific hook.
- Create a clear narrative progression.
- Use short paragraphs.
- Use useful Markdown headings.
- Use bullets where they improve readability.
- Use selective **bold** emphasis.
- Explain the underlying product or growth lesson.
- Include concrete examples ONLY when supported by the evidence.
- End with a specific and actionable takeaway.
- Make the piece useful to a product or growth practitioner.

GROUNDING REQUIREMENTS:
- Every factual claim must come from the supplied transcript evidence.
- Preserve source markers such as [S1], [S2], and [S3].
- Put the relevant source marker immediately after the supported claim.
- Do not invent statistics, companies, people, studies, anecdotes, quotes,
  frameworks, or examples.
- Do not use general knowledge.
- Do not mention information that is absent from the evidence.
- Do not fabricate source markers.
- Do not add a References section.
- If the evidence is insufficient for a requested point, explicitly state
  that the available transcript evidence does not establish it.

IMPORTANT:
The grounded answer is an interpretation of the evidence, not an
additional source. Treat it as a summary only and do not introduce facts
that are absent from the transcript evidence.

OUTPUT:
Return Markdown only.
Do not explain your process.
"""


class Ship30GroundingError(ProviderError):
    """Raised when generated Ship 30 content violates grounding rules."""


class Ship30Skill:
    """Generate a grounded Ship 30 for 30 style essay."""

    name = "ship30_for_30"

    def build_prompt(
        self,
        topic: str,
        grounded_answer: str,
        evidence: str,
    ) -> str:
        return f"""
TOPIC:
{topic}

GROUNDED ANSWER:
{grounded_answer}

TRANSCRIPT EVIDENCE:
{evidence}

SOURCE MARKER RULE:
The transcript evidence above is labeled [S1], [S2], [S3], etc.
Use those exact markers when making claims based on the corresponding
evidence.

TASK:
Write the final approximately 1,250-word Ship 30 for 30 essay.

The essay should:

1. Start with a compelling hook.
2. Introduce the central problem or tension.
3. Develop the lesson using only the transcript evidence.
4. Translate the lesson into practical product/growth actions.
5. End with a concise, useful takeaway.

Before writing each factual claim, ask:
"Can I point to this exact idea in the supplied evidence?"

If the answer is no, leave the claim out.

Do not invent examples to make the essay more interesting.

GROUNDING:
- Use only the supplied transcript evidence.
- Keep [S1], [S2], [S3] citations beside the claims they support.
- Never create a citation that does not exist in the evidence.
- Never introduce an external company, person, statistic, study, quote,
  anecdote, or framework.
- Do not use knowledge from your pretrained model.
""".strip()

    @staticmethod
    def _extract_source_markers(text: str) -> set[str]:
        """Extract source markers such as [S1] and [S2]."""
        return set(re.findall(r"\[S\d+\]", text))

    @staticmethod
    def _word_count(text: str) -> int:
        """Return an approximate word count."""
        return len(re.findall(r"\b[\w'-]+\b", text))

    def _validate(
        self,
        essay: str,
        evidence: str,
    ) -> None:
        """Validate basic output quality and citation grounding."""

        if not essay.strip():
            raise Ship30GroundingError(
                "Ship 30 generation returned empty content."
            )

        word_count = self._word_count(essay)

        # Assignment target is approximately 1,250 words.
        # We allow a practical range so smaller local models can still
        # produce useful content.
        if word_count < 700:
            raise Ship30GroundingError(
                f"Ship 30 essay is too short ({word_count} words)."
            )

        if word_count > 1800:
            raise Ship30GroundingError(
                f"Ship 30 essay is too long ({word_count} words)."
            )

        evidence_markers = self._extract_source_markers(evidence)
        essay_markers = self._extract_source_markers(essay)

        invalid_markers = essay_markers - evidence_markers

        if invalid_markers:
            invalid = ", ".join(sorted(invalid_markers))

            raise Ship30GroundingError(
                f"Ship 30 generated unsupported source markers: {invalid}."
            )

        # Retrieved evidence is expected to have source markers.
        # Require the generated essay to preserve them.
        if evidence.strip() and not essay_markers:
            raise Ship30GroundingError(
                "Ship 30 essay contains no source citations."
            )

    def generate(
        self,
        topic: str,
        grounded_answer: str,
        evidence: str,
        chat_provider: ChatProvider,
    ) -> str:
        """Generate and validate a grounded Ship 30 essay."""

        prompt = self.build_prompt(
            topic=topic,
            grounded_answer=grounded_answer,
            evidence=evidence,
        )

        response = chat_provider.generate(
            system_prompt=SHIP30_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        essay = response.text.strip()

        self._validate(
            essay=essay,
            evidence=evidence,
        )

        return essay