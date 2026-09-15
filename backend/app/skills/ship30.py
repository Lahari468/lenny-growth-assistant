"""
Ship 30 for 30 Skill.
Encodes Dickie Bush & Nicolas Cole's viral atomic essay principles into structured essays (~1,250 words)
grounded in authentic Lenny's Podcast transcript insights.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.skills.base import BaseSkill, SkillResult
from app.retrieval.vector_store import vector_store
from app.providers.factory import provider_factory

logger = logging.getLogger("lenny_growth.skills.ship30")

SHIP30_SYSTEM_PROMPT = """You are an expert ghostwriter and growth strategist trained in the Ship 30 for 30 writing framework by Dickie Bush and Nicolas Cole.
Your mission is to turn authoritative insights from Lenny's Podcast into a high-impact, high-retention atomic essay (~1,250 words).

Ship 30 Writing Architecture Rules:
1. THE HEADLINE HOOK: A bold, curiosity-driven headline that promises a clear transformation or framework.
2. THE LEAD-IN: Use the 1-3-1 cadence (1 sentence punchline, 3 sentences establishing the high stakes, 1 sentence pivot).
3. SKIMMABLE STRUCTURE: Use clear, action-oriented subheadings (H2/H3). Never write walls of text.
4. SELECTIVE BOLD EMPHASIS: Bold key phrases, core mental models, and contrarian rules so skimmers extract 80% of the value in 20 seconds.
5. BULLET LISTS: Break complex processes into punchy bullet points.
6. TRANSCRIPT GROUNDING: Every core argument must be grounded in the provided Lenny's Podcast transcript evidence. Mention the guest by name and quote their core thesis.
7. ACTIONABLE TAKEAWAY: Conclude with a concrete, step-by-step checklist or challenge the reader can execute tomorrow morning.
8. TARGET LENGTH: Aim for a comprehensive, deep-dive atomic essay of approximately 1,000 to 1,250 words. Do not provide a shallow summary."""

class Ship30Skill(BaseSkill):
    async def execute(
        self,
        query: str,
        history: List[Dict[str, str]],
        db: AsyncSession,
        session_id: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> SkillResult:
        logger.info("Executing Ship30Skill for query: '%s'", query[:50])

        # 1. Retrieve relevant transcript context
        citations = await vector_store.search(db, query=query, top_k=5, min_similarity=0.15)

        context_blocks = []
        for i, c in enumerate(citations, 1):
            context_blocks.append(
                f"[Source {i}] Episode: {c.episode_title} | Guest: {c.guest} | URL: {c.source_url}\n"
                f"Transcript Excerpt:\n{c.snippet}\n"
            )
        transcript_context = "\n---\n".join(context_blocks) if context_blocks else "General product and growth principles."

        prompt = f"""<transcript_evidence>
{transcript_context}
</transcript_evidence>

Topic / Request:
{query}

Write a comprehensive, deep-dive Ship 30 for 30 style atomic essay (~1,250 words) based on the transcript evidence above. Ensure you include:
- A magnetic headline and 1-3-1 opening hook
- Subheadings and bulleted frameworks
- Bold emphasis for skimmability
- Explicit attribution to the guest and transcript ideas
- A dedicated 'Actionable Takeaway' section at the end"""

        provider = provider_factory.get_provider(provider_name)
        response = await provider.generate(
            prompt=prompt,
            system_prompt=SHIP30_SYSTEM_PROMPT,
            model=model_name,
            temperature=0.4,
            max_tokens=2500,
        )

        essay_content = response.content
        validation_metrics = self.validate_ship30_output(essay_content)

        return SkillResult(
            content=essay_content,
            intent="ship30",
            citations=citations,
            metadata={
                "validation": validation_metrics,
                "provider": provider_name or provider_factory.get_active_provider_name(),
            }
        )

    def validate_ship30_output(self, text: str) -> Dict[str, Any]:
        """Validate Ship 30 structural elements and word counts."""
        words = re.findall(r"\b\w+\b", text)
        word_count = len(words)
        
        has_headings = bool(re.search(r"^#{1,4}\s+", text, re.MULTILINE))
        has_bullets = bool(re.search(r"^\s*[-*]\s+", text, re.MULTILINE))
        has_bold = bool(re.search(r"\*\*[^*]+\*\*", text))
        has_takeaway = any(k in text.lower() for k in ["takeaway", "actionable", "next step", "checklist", "playbook"])

        return {
            "word_count": word_count,
            "has_headings": has_headings,
            "has_bullets": has_bullets,
            "has_bold_emphasis": has_bold,
            "has_actionable_takeaway": has_takeaway,
            "meets_length_target": word_count >= 500,  # Graceful threshold for compact models
        }
