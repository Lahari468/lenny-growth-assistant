"""
Conversational Agent Orchestrator.
Coordinates intent classification, skill dispatch, conversational context, and persistence.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import SessionModel, MessageModel, ArtifactModel
from app.agent.router import intent_router
from app.skills.grounded_qa import GroundedQASkill
from app.skills.ship30 import Ship30Skill
from app.skills.artifact_generator import ArtifactGeneratorSkill
from app.schemas.message import MessageResponse, Citation

logger = logging.getLogger("lenny_growth.agent.orchestrator")

class AgentOrchestrator:
    def __init__(self):
        artifact_skill = ArtifactGeneratorSkill()
        self.skills = {
            "grounded_qa": GroundedQASkill(),
            "ship30": Ship30Skill(),
            "artifact_generation": artifact_skill,
            "markdown_artifact": artifact_skill,
            "html_artifact": artifact_skill,
        }



    async def process_message(
        self,
        db: AsyncSession,
        session_id: str,
        user_content: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> MessageResponse:
        logger.info("Orchestrator processing message for session %s: '%s'", session_id, user_content[:40])

        # 1. Verify session exists
        session = await db.get(SessionModel, session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        # Update session title if default
        if session.title == "New Growth Chat" and user_content:
            derived_title = user_content[:45].strip() + ("..." if len(user_content) > 45 else "")
            session.title = derived_title

        # 2. Persist user message
        user_msg = MessageModel(
            session_id=session_id,
            role="user",
            content=user_content,
        )
        db.add(user_msg)
        await db.commit()

        # 3. Retrieve conversation history
        stmt = (
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
        )
        history_rows = (await db.execute(stmt)).scalars().all()
        history: List[Dict[str, str]] = [
            {"role": m.role, "content": m.content}
            for m in history_rows if m.id != user_msg.id
        ]

        # 4. Route intent
        intent = intent_router.classify_intent(user_content)

        if intent == "greeting":
            greeting_content = (
                "👋 Hello! I am **The Lenny Growth Assistant**.\n\n"
                "I provide product and growth frameworks strictly grounded in **Lenny's Podcast transcripts**, "
                "generate **Ship 30 for 30 atomic essays** (~1,250 words), and create **interactive sandboxed HTML artifacts**.\n\n"
                "Here are some great topics to explore:\n"
                "- **Shreyas Doshi**: High Agency, problem framing, product work destruction.\n"
                "- **Elena Verna**: B2B Product-Led Growth (PLG), reverse trials, activation.\n"
                "- **Brian Chesky**: Founder Mode, design reviews, Airbnb product leadership.\n"
                "- **Gustaf Alströmer**: Cohort retention curves, North Star metrics.\n"
                "- **Casey Winters**: Compounding growth loops, SEO loops vs funnels.\n\n"
                "Try asking:\n"
                "- *'How did Shreyas Doshi define High Agency?'*\n"
                "- *'Write a Ship 30 essay on Elena Verna's reverse trials'*\n"
                "- *'Generate an HTML growth metric dashboard based on Gustaf Alströmer'*\n\n"
                "What product or growth challenge are you working on?"
            )
            assistant_msg = MessageModel(
                session_id=session_id,
                role="assistant",
                content=greeting_content,
                intent="greeting",
                citations_json="[]",
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return MessageResponse(
                id=assistant_msg.id,
                session_id=session_id,
                role="assistant",
                content=assistant_msg.content,
                intent="greeting",
                citations=[],
                created_at=assistant_msg.created_at,
                has_artifact=False,
                artifact_id=None,
            )

        skill = self.skills.get(intent, self.skills["grounded_qa"])


        # 5. Execute skill
        skill_result = await skill.execute(
            query=user_content,
            history=history,
            db=db,
            session_id=session_id,
            provider_name=provider_name,
            model_name=model_name,
        )

        # 6. Prepare citations JSON
        citations_data = [c.model_dump() for c in skill_result.citations] if skill_result.citations else []

        # 7. Persist assistant message
        assistant_msg = MessageModel(
            session_id=session_id,
            role="assistant",
            content=skill_result.content,
            intent=skill_result.intent,
            citations_json=json.dumps(citations_data),
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        # If an artifact was generated, link its message_id
        if skill_result.has_artifact and skill_result.artifact_id:
            art = await db.get(ArtifactModel, skill_result.artifact_id)
            if art:
                art.message_id = assistant_msg.id
                await db.commit()

        return MessageResponse(
            id=assistant_msg.id,
            session_id=session_id,
            role="assistant",
            content=assistant_msg.content,
            intent=skill_result.intent,
            citations=skill_result.citations,
            created_at=assistant_msg.created_at,
            has_artifact=skill_result.has_artifact,
            artifact_id=skill_result.artifact_id,
        )

orchestrator = AgentOrchestrator()
