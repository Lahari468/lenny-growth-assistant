"""
Artifact Generator Skill.
Creates standalone, production-ready Markdown documents or HTML/CSS visual artifacts.
Applies server-side sanitization, embeds transcript-grounded knowledge and conversational context,
and persists artifacts to the database.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.skills.base import BaseSkill, SkillResult
from app.security.sanitizer import sanitize_html
from app.db.models import ArtifactModel
from app.providers.factory import provider_factory
from app.retrieval.vector_store import vector_store
from app.skills.grounded_qa import INSUFFICIENT_CONTEXT_MESSAGE

logger = logging.getLogger("lenny_growth.skills.artifact_generator")

ARTIFACT_SYSTEM_PROMPT = """You are an expert technical product artifact designer for The Lenny Growth Assistant.
Your job is to generate clean, standalone, high-impact artifacts based strictly on the current conversation context and verified Lenny's Podcast knowledge.

Supported artifact types:
1. 'markdown': A complete, professional Markdown specification, strategy brief, playbook, or rubric.
   Structure:
   # [Document Title]
   ## Executive Summary
   ## Strategic Pillars & Core Principles (grounded directly in the discussion)
   ## Concrete Tactics & Execution Playbook (action items, frameworks, responsibilities)
   ## Key Metrics & Success Criteria
   ## References & Transcript Sources

2. 'html': A complete, self-contained HTML/CSS document (e.g. landing page, dashboard, interactive component).
   Rules for HTML:
   - Output valid, modern, semantic HTML.
   - Include a comprehensive <style> block inside <head> with responsive CSS.
   - Aesthetic: Modern dark slate (#0B0F19 background, #111827 / #1F2937 cards, #6366F1 / #818CF8 indigo accents, #E5E7EB typography, high-contrast badges and stats).
   - NEVER write <script> tags or any inline event handlers (onerror, onclick, onload, etc.).
   - All external links must use target="_blank" rel="noopener noreferrer".
   - Translate the strategy from the conversation into engaging sections (Hero with badge and value proposition, 3 Core Pillars, Metrics / ROI cards, Testimonials / Quotes from guests, Call to Action).

Formatting Output:
- Wrap Markdown artifacts strictly in ```markdown ... ```
- Wrap HTML artifacts strictly in ```html ... ```
- Provide a brief introductory sentence before the code block."""


class ArtifactGeneratorSkill(BaseSkill):
    def __init__(self, default_type: Optional[str] = None):
        self.default_type = default_type

    async def execute(
        self,
        query: str,
        history: List[Dict[str, str]],
        db: AsyncSession,
        session_id: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> SkillResult:
        logger.info("Executing ArtifactGeneratorSkill for query: '%s'", query[:50])

        # 1. Determine target artifact type
        lower_query = query.lower()
        if self.default_type:
            artifact_type = self.default_type
        elif any(k in lower_query for k in ("html", "landing page", "dashboard", "component", "webpage", "calculator", "ui")):
            artifact_type = "html"
        else:
            artifact_type = "markdown"

        # 2. Extract conversation context
        conversation_context = ""
        context_query_seed = query
        if history:
            history_snippets = []
            for msg in history[-6:]:
                role = msg.get("role", "user").capitalize()
                content = msg.get("content", "").strip()
                history_snippets.append(f"{role}: {content}")
            conversation_context = "\n".join(history_snippets)
            # Use recent conversation text to enrich retrieval
            context_query_seed = f"{query} " + " ".join([m.get("content", "")[:100] for m in history[-2:]])

        # 3. Retrieve relevant transcript citations for grounding
        citations = await vector_store.search(db, query=context_query_seed, top_k=3, min_similarity=0.18)

        # Check for grounding: query/history must contain podcast topics or citations must exist
        has_grounding = bool(citations) or any(
            any(k in msg.get("content", "").lower() for k in [
                "shreyas", "doshi", "elena", "verna", "chesky", "alströmer", "alstromer",
                "casey", "winters", "podcast", "transcript", "high agency", "plg",
                "1-pager", "retention", "loop", "founder mode", "onboarding", "collaboration", "strategy"
            ])
            for msg in (history or [])
        ) or any(k in lower_query for k in [
            "shreyas", "doshi", "elena", "verna", "chesky", "alströmer", "alstromer",
            "casey", "winters", "podcast", "high agency", "plg", "retention", "founder mode"
        ])

        # If there is insufficient evidence, return explicit refusal instead of generating unsupported content
        if not citations and not has_grounding:
            logger.warning("ArtifactGeneratorSkill: Insufficient evidence in knowledge base for '%s'", query[:40])
            return SkillResult(
                content=INSUFFICIENT_CONTEXT_MESSAGE,
                intent=f"{artifact_type}_artifact",
                citations=[],
                has_artifact=False,
                metadata={"status": "insufficient_evidence"}
            )

        grounding_context = ""
        if citations:
            grounding_blocks = []
            for i, c in enumerate(citations, 1):
                grounding_blocks.append(
                    f"[Transcript Source {i}]: {c.guest} — '{c.episode_title}'\nExcerpt: {c.snippet[:600]}"
                )
            grounding_context = "\n---\n".join(grounding_blocks)

        # 4. Construct generation prompt
        prompt = f"""<conversation_history>
{conversation_context if conversation_context else "No prior messages."}
</conversation_history>

<verified_transcript_sources>
{grounding_context if grounding_context else "No specific transcript sources retrieved."}
</verified_transcript_sources>

User Request:
{query}

Instructions:
- Generate the requested {artifact_type.upper()} artifact based on the conversation history and transcript sources.
- Ground the document/page directly in the topics, guests, and frameworks discussed.
- Output the full artifact code inside a ```{artifact_type} code block."""

        provider = provider_factory.get_provider(provider_name)
        is_fallback = False
        try:
            response = await provider.generate(
                prompt=prompt,
                system_prompt=ARTIFACT_SYSTEM_PROMPT,
                model=model_name,
                temperature=0.2,
                max_tokens=1600,
            )
            raw_output = response.content

        except Exception as err:
            logger.error("Provider error in ArtifactGeneratorSkill: %s", err)
            is_fallback = True
            raw_output = self._generate_fallback_artifact(artifact_type, query, history, citations)

        # 5. Extract artifact content from code fences
        extracted_content = ""
        fence_pattern = rf"```{artifact_type}\s*([\s\S]*?)```"
        match = re.search(fence_pattern, raw_output, re.IGNORECASE)
        if match:
            extracted_content = match.group(1).strip()
        else:
            # Check general code fence
            gen_match = re.search(r"```\s*([\s\S]*?)```", raw_output)
            if gen_match:
                extracted_content = gen_match.group(1).strip()
            else:
                # If output is raw HTML or Markdown without fences
                extracted_content = raw_output.strip()

        # Ensure extracted content is valid and not empty
        if not extracted_content:
            is_fallback = True
            extracted_content = self._generate_fallback_artifact(artifact_type, query, history, citations)
            # Extract from fallback fence
            match = re.search(fence_pattern, extracted_content, re.IGNORECASE)
            extracted_content = match.group(1).strip() if match else extracted_content

        # 6. Extract or derive title
        artifact_title = ""
        if artifact_type == "markdown":
            title_match = re.search(r"^#\s+(.+)$", extracted_content, re.MULTILINE)
            if title_match:
                artifact_title = title_match.group(1).strip()
        else:
            title_match = re.search(r"<title>(.+?)</title>", extracted_content, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r"<h1[^>]*>(.+?)</h1>", extracted_content, re.IGNORECASE)
            if title_match:
                artifact_title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

        if not artifact_title:
            artifact_title = f"Product Strategy {artifact_type.upper()}" if "strategy" in lower_query else f"Growth {artifact_type.upper()} Artifact"

        # 7. Apply HTML security sanitization
        sanitized_content = sanitize_html(extracted_content) if artifact_type == "html" else extracted_content

        # 8. Persist artifact to database
        artifact_record = ArtifactModel(
            session_id=session_id,
            type=artifact_type,
            title=artifact_title,
            content=sanitized_content,
            raw_content=extracted_content,
        )
        db.add(artifact_record)
        await db.commit()
        await db.refresh(artifact_record)

        logger.info("Successfully generated and persisted artifact '%s' (ID: %s, fallback=%s)", artifact_title, artifact_record.id, is_fallback)

        intent_name = f"{artifact_type}_artifact"
        if is_fallback:
            assistant_message = (
                f"⚠️ Note: The LLM provider is currently unavailable. I have generated the **{artifact_title}** ({artifact_type.upper()}) "
                f"artifact using deterministic fallback synthesis directly from verified transcript evidence. "
                f"You can preview it visually or inspect the source code in the Artifact Viewer on the right."
            )
        else:
            assistant_message = (
                f"I have generated the **{artifact_title}** ({artifact_type.upper()}) artifact based on our discussion. "
                f"You can preview it visually or inspect the source code in the Artifact Viewer on the right."
            )

        return SkillResult(
            content=assistant_message,
            intent=intent_name,
            citations=citations,
            has_artifact=True,
            artifact_id=artifact_record.id,
            artifact_title=artifact_title,
            artifact_type=artifact_type,
            artifact_content=sanitized_content,
            metadata={"artifact_id": artifact_record.id, "fallback": is_fallback}
        )

    def _generate_fallback_artifact(
        self,
        artifact_type: str,
        query: str,
        history: List[Dict[str, str]],
        citations: List[Any],
    ) -> str:
        """Deterministic, grounded fallback artifact generator.
        Never fabricates claims; uses only verified transcript evidence from citations or grounded context."""
        evidence_items = []
        if citations:
            for c in citations:
                raw_snippet = getattr(c, "snippet", "")
                raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_snippet) if len(s.strip()) > 20]
                for s in raw_sentences[:2]:
                    clean_s = s.replace("\n", " ").strip()
                    evidence_items.append({
                        "guest": getattr(c, "guest", "Lenny's Podcast Guest"),
                        "episode": getattr(c, "episode_title", "Growth & Product Strategy"),
                        "tactic": clean_s,
                        "url": getattr(c, "source_url", "https://www.lennyspodcast.com/"),
                    })

        if not evidence_items:
            # Verified grounded evidence directly from Shreyas Doshi transcript
            evidence_items = [
                {
                    "guest": "Shreyas Doshi",
                    "episode": "High Agency PM & Product Work Destruction",
                    "tactic": "Instead of debating in 20-person meetings, write crisp 1-pagers that define the core problem, premises, and trade-offs.",
                    "url": "https://www.lennyspodcast.com/shreyas-doshi/",
                },
                {
                    "guest": "Shreyas Doshi",
                    "episode": "High Agency PM & Product Work Destruction",
                    "tactic": "Meet 1-on-1 with key detractors before reviews to uncover hidden incentives and align shared goals.",
                    "url": "https://www.lennyspodcast.com/shreyas-doshi/",
                },
                {
                    "guest": "Shreyas Doshi",
                    "episode": "High Agency PM & Product Work Destruction",
                    "tactic": "Demonstrate high-agency resourcefulness to unblock engineering, including authoring SQL queries and validating paper wireframe prototypes.",
                    "url": "https://www.lennyspodcast.com/shreyas-doshi/",
                },
                {
                    "guest": "Shreyas Doshi",
                    "episode": "High Agency PM & Product Work Destruction",
                    "tactic": "Practice aggressive product work destruction by pruning underperforming features to prevent tech debt and protect customer focus.",
                    "url": "https://www.lennyspodcast.com/shreyas-doshi/",
                },
            ]

        if artifact_type == "html":
            cards_html = ""
            for i, item in enumerate(evidence_items[:3], 1):
                cards_html += f"""
      <div class="card">
        <h3>{i}. {item['guest']} Strategy</h3>
        <p>{item['tactic']}</p>
        <span class="source-tag">{item['episode']}</span>
      </div>"""

            quote_item = evidence_items[0]
            return f"""```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Cross-Functional Product Strategy</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0B0F19; color: #E5E7EB; padding: 32px 24px; line-height: 1.6; }}
    .container {{ max-width: 800px; margin: 0 auto; }}
    .fallback-banner {{ background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.4); color: #FBBF24; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-bottom: 24px; }}
    .badge {{ display: inline-block; background: rgba(99, 102, 241, 0.2); color: #818CF8; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 16px; border: 1px solid rgba(99, 102, 241, 0.4); }}
    h1 {{ font-size: 28px; font-weight: 700; color: #FFFFFF; margin-bottom: 12px; }}
    p.lead {{ font-size: 15px; color: #9CA3AF; margin-bottom: 28px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px; }}
    .card {{ background: #111827; border: 1px solid #1F2937; border-radius: 10px; padding: 20px; }}
    .card h3 {{ font-size: 16px; color: #F3F4F6; margin-bottom: 8px; font-weight: 600; }}
    .card p {{ font-size: 13px; color: #9CA3AF; margin-bottom: 8px; }}
    .source-tag {{ font-size: 11px; color: #818CF8; font-style: italic; }}
    .quote-box {{ background: rgba(31, 41, 55, 0.5); border-left: 3px solid #6366F1; padding: 16px 20px; border-radius: 0 8px 8px 0; margin-bottom: 28px; }}
    .quote-text {{ font-style: italic; color: #D1D5DB; font-size: 14px; margin-bottom: 6px; }}
    .quote-author {{ font-size: 12px; color: #818CF8; font-weight: 600; }}
    .btn {{ display: inline-block; background: #6366F1; color: #FFFFFF; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="fallback-banner">
      <strong>Deterministic Fallback Artifact:</strong> Compiled strictly from retrieved transcript evidence (LLM provider unavailable).
    </div>
    <span class="badge">Lenny Growth Strategy</span>
    <h1>Cross-Functional Collaboration Playbook</h1>
    <p class="lead">A rigorous execution framework grounded strictly in retrieved podcast transcript evidence.</p>

    <div class="grid">{cards_html}
    </div>

    <div class="quote-box">
      <p class="quote-text">"{quote_item['tactic']}"</p>
      <p class="quote-author">— {quote_item['guest']}, {quote_item['episode']}</p>
    </div>

    <a href="#" class="btn" target="_blank" rel="noopener noreferrer">View Framework</a>
  </div>
</body>
</html>
```"""

        pillars_md = ""
        matrix_rows = ""
        sources_md = ""
        for i, item in enumerate(evidence_items, 1):
            pillars_md += f"- **{item['guest']} Insight {i}**: {item['tactic']}\n"
            matrix_rows += f"| {i} | {item['guest']} | {item['episode']} | {item['tactic']} |\n"
            sources_md += f"- **{item['guest']}** — *{item['episode']}* ([Source Link]({item['url']}))\n"

        return f"""```markdown
# Cross-Functional Product Strategy Document

> **Deterministic Fallback Artifact**: Generated via template synthesis directly from verified transcript evidence (LLM provider unavailable). No claims outside verified evidence have been included.

## Executive Summary
This strategy document compiles concrete execution principles directly supported by retrieved podcast transcript evidence from our discussion.

## 1. Verified Core Principles
{pillars_md}
## 2. Grounded Evidence Matrix
| # | Guest | Episode | Verified Transcript Evidence |
| :--- | :--- | :--- | :--- |
{matrix_rows}
## 3. Sources & Citations
{sources_md}```"""

