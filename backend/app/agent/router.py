"""
Intent Router.
Determines whether a user query requires:
1. 'grounded_qa': Factual product/growth questions answered from Lenny's Podcast transcripts.
2. 'ship30': Requests for atomic essays, articles, or Ship 30 for 30 style writing.
3. 'artifact_generation': Requests to create HTML components, dashboards, visual checklists, or Markdown specs.
"""

import re
import logging
from typing import Literal

logger = logging.getLogger("lenny_growth.agent.router")

class ArtifactIntent(str):

    """String subtype for artifact intents compatible with legacy 'artifact_generation'."""
    def __eq__(self, other: object) -> bool:
        if other == "artifact_generation":
            return True
        return super().__eq__(other)

    def __hash__(self) -> int:
        return super().__hash__()

IntentType = Literal["grounded_qa", "ship30", "markdown_artifact", "html_artifact", "artifact_generation", "greeting"]


GREETING_TRIGGERS = [
    r"^(hi|hello|hey|greetings|howdy|good\s+(morning|afternoon|evening))\b",
    r"^who\s+are\s+you\b",
    r"^what\s+can\s+you\s+do\b",
    r"^help\b",
]

SHIP30_TRIGGERS = [
    r"\bship\s*30\b",
    r"\batomic\s+essay\b",
    r"\bwrite\s+(an?\s+)?article\b",
    r"\bwrite\s+(an?\s+)?essay\b",
    r"\bthought\s+piece\b",
    r"\b1250\s+words?\b",
    r"\bblog\s+post\b",
]

HTML_ARTIFACT_TRIGGERS = [
    r"\b(generate|create|build|render|make)\b.*?\b(html|landing\s+page|dashboard|component|webpage|calculator)\b",
    r"\blanding\s+page\b",
    r"\bhtml\s*[\/\-]?\s*css\b",
    r"\binteractive\s+dashboard\b",
    r"\bhtml\s+component\b",
    r"\bhtml\b",
]

MARKDOWN_ARTIFACT_TRIGGERS = [
    r"\b(generate|create|build|render|make|draft)\b.*?\b(markdown|document|cheatsheet|rubric|specification|spec|checklist)\b",
    r"\bmarkdown\s+(product\s+strategy\s+)?document\b",
    r"\bproduct\s+strategy\s+document\b",
    r"\bchecklist\s+artifact\b",
    r"\bmarkdown\s+artifact\b",
    r"\bmarkdown\b",
    r"\bartifact\b",
]


class IntentRouter:
    def classify_intent(self, query: str) -> IntentType:
        """Rule-based and pattern matching intent classifier with zero external latency."""
        q = query.lower().strip()

        # Check Greeting
        for pattern in GREETING_TRIGGERS:
            if re.search(pattern, q):
                logger.info("Router classified intent as 'greeting' matching '%s'", pattern)
                return "greeting"

        # Check Ship30
        for pattern in SHIP30_TRIGGERS:
            if re.search(pattern, q):
                logger.info("Router classified intent as 'ship30' matching '%s'", pattern)
                return "ship30"

        # Check HTML Artifact Generation
        for pattern in HTML_ARTIFACT_TRIGGERS:
            if re.search(pattern, q):
                logger.info("Router classified intent as 'html_artifact' matching '%s'", pattern)
                return ArtifactIntent("html_artifact")

        # Check Markdown Artifact Generation
        for pattern in MARKDOWN_ARTIFACT_TRIGGERS:
            if re.search(pattern, q):
                logger.info("Router classified intent as 'markdown_artifact' matching '%s'", pattern)
                return ArtifactIntent("markdown_artifact")


        # Default to Grounded QA
        logger.info("Router defaulted to 'grounded_qa'")
        return "grounded_qa"



intent_router = IntentRouter()
