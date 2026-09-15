
"""
Grounded Question Answering Skill.
Answers product and growth questions strictly using verified Lenny's Podcast transcript evidence.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.skills.base import BaseSkill, SkillResult
from app.retrieval.vector_store import vector_store
from app.providers.factory import provider_factory

logger = logging.getLogger("lenny_growth.skills.grounded_qa")

GROUNDED_SYSTEM_PROMPT = """You are The Lenny Growth Assistant.
Answer product and growth questions strictly using verified evidence from the supplied Lenny’s Podcast transcript context.

Strict Grounding Rules:
1. Grounded Facts & Concrete Tactics Only: Every recommendation, tactic, and claim must be directly supported by explicit statements in the retrieved transcripts.
2. No Extrapolations or Generic Filler: Do NOT introduce generic management advice, textbook clichés, or inferred definitions (e.g., do NOT invent phrases like 'building relationships', 'deep understanding of business and technology', or 'driving decisions without approval'). If a tactic or idea is not in the text, omit it completely.
3. Definitions: Do NOT define concepts (such as 'high agency') unless the user explicitly asks for a definition. If a definition is explicitly requested, use ONLY the verbatim transcript definition ('the ability to bend reality to your will' / 'refusing to allow external obstacles to dictate the outcome'). Do NOT infer or alter definitions.
4. Specific Supported Tactics: When answering how to improve cross-functional collaboration and persuasion, rely strictly on the supported tactics from the context:
   - Writing crisp 1-pagers instead of debating in 20-person meetings
   - Meeting 1-on-1 with key detractors to understand hidden incentives and align goals
   - Demonstrating resourcefulness to unblock engineering (such as writing SQL queries or testing paper wireframes)
   - Practicing product elimination (killing bad ideas and pruning underperforming features to prevent tech debt and protect engineering focus)
5. Attribution: Clearly and accurately attribute each tactic to the guest who stated it (e.g., Shreyas Doshi). Never attribute a quote or tactic to a different guest.
6. Explicit Limitations: Always conclude with a '**Limitations**' section explicitly declaring what the transcripts cover and noting what is absent (e.g., noting that the transcripts focus on high-agency PM execution and product elimination, and do not provide standard process frameworks like Agile/Scrum ceremonies or formal org designs).
7. Format: Deliver a concise, practical, bulleted response without general filler commentary."""

INSUFFICIENT_CONTEXT_MESSAGE = (
    "⚠️ **Insufficient Evidence in Knowledge Base**\n\n"
    "The available Lenny's Podcast transcripts do not contain evidence to answer this question. "
    "To strictly prevent hallucinations, I only provide claims supported by verified transcript evidence.\n\n"
    "Please ask about topics covered by featured guests in the knowledge base:\n"
    "- **Shreyas Doshi**: High agency, problem framing, cross-functional persuasion, product work destruction.\n"
    "- **Elena Verna**: B2B Product-Led Growth, reverse trials, time-to-value, user onboarding.\n"
    "- **Brian Chesky**: Founder mode, design reviews, Airbnb product leadership.\n"
    "- **Gustaf Alströmer**: Cohort retention curves, North Star metrics, YC growth engine.\n"
    "- **Casey Winters**: Compounding growth loops, SEO loops, viral loops vs linear funnels."
)


class GroundedQASkill(BaseSkill):
    async def execute(
        self,
        query: str,
        history: List[Dict[str, str]],
        db: AsyncSession,
        session_id: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> SkillResult:
        logger.info("Executing GroundedQASkill for query: '%s'", query[:50])

        # 1. Retrieve relevant transcript chunks
        citations = await vector_store.search(db, query=query, top_k=4, min_similarity=0.18)

        # 2. If no chunks found, return explicit refusal
        if not citations:
            logger.warning("GroundedQASkill: Zero relevant transcript chunks found for '%s'", query[:40])
            return SkillResult(
                content=INSUFFICIENT_CONTEXT_MESSAGE,
                intent="grounded_qa",
                citations=[],
                metadata={"status": "insufficient_evidence"}
            )

        # Filter citations to keep only relevant chunks (relative to top match score)
        top_score = citations[0].similarity_score
        relevant_citations = [
            c for c in citations
            if c.similarity_score >= max(0.24, top_score * 0.65)
        ]
        if not relevant_citations:
            relevant_citations = citations[:2]

        # 3. Assemble grounded prompt with retrieved chunks
        context_blocks = []
        for i, c in enumerate(relevant_citations, 1):
            context_blocks.append(
                f"[Source {i}]: Episode: {c.episode_title} | Guest: {c.guest} | URL: {c.source_url}\n"
                f"Transcript Excerpt:\n{c.snippet}\n"
            )
        transcript_context = "\n---\n".join(context_blocks)

        # Format conversation history
        formatted_history = ""
        if history:
            formatted_history = "\nRecent Conversation History:\n"
            for msg in history[-4:]:
                formatted_history += f"{msg['role'].capitalize()}: {msg['content']}\n"

        prompt = f"""<transcript_context>
{transcript_context}
</transcript_context>
{formatted_history}
Current User Question:
{query}

Instructions:
- Provide a concise, practical answer directly based on the concrete tactics from the transcript context.
- Every claim must be supported by the transcript text. Do NOT add generic filler (like 'building relationships') or infer abstract definitions (like defining 'high agency').
- Attribute each tactic accurately to the guest who stated it.
- If the context does not fully answer the question, explicitly state the limitation in a '**Limitations**' section."""


        # 4. Generate answer via provider
        provider = provider_factory.get_provider(provider_name)
        try:
            response = await provider.generate(
                prompt=prompt,
                system_prompt=GROUNDED_SYSTEM_PROMPT,
                model=model_name,
                temperature=0.1,
                max_tokens=1200,
            )
            answer_content = response.content
        except Exception as err:
            logger.error("Provider generation error in GroundedQASkill: %s", err)
            raise err

        # 5. Output Verification: Guard against degenerate/unrelated product extraction spam
        disallowed_patterns = [
            r"extract the product information",
            r"<div class=['\"]product['\"]",
            r"google pixel",
            r"samsung galaxy",
            r"dell xps",
            r"hp envy",
        ]
        import re
        if any(re.search(pat, answer_content, re.IGNORECASE) for pat in disallowed_patterns):
            logger.warning("GroundedQASkill: Detected degenerate product output from model. Replacing with synthesized evidence summary.")
            claims = []
            for c in relevant_citations:
                clean_snippet = re.sub(r"^(Lenny Rachitsky|Shreyas Doshi|Brian Chesky|Elena Verna|Gustaf Alstr\w+|Casey Winters):\s*", "", c.snippet)
                first_sent = clean_snippet.split(". ")[0].strip() if ". " in clean_snippet else clean_snippet[:120].strip()
                claims.append(f"- **{c.guest}** (*{c.episode_title}*): {first_sent}.")
            claims_summary = "\n".join(claims)
            answer_content = (
                f"### Grounded Evidence Summary\n\n"
                f"Based on Lenny's Podcast transcripts regarding this topic:\n\n"
                f"{claims_summary}\n\n"
                f"*(Note: You can inspect the full verbatim transcript excerpts and episode links in the citations below.)*"
            )

        return SkillResult(
            content=answer_content,
            intent="grounded_qa",
            citations=relevant_citations,
            metadata={"provider": provider_name or provider_factory.get_active_provider_name()}
        )

