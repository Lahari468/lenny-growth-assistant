"""
Pytest configuration and test fixtures.
Provides isolated test database, test client, and mock LLM providers.
"""

import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.db.database import Base, get_db


from app.main import app
from app.providers.base import LLMProvider, LLMResponse
from app.providers.factory import provider_factory

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

class MockLLMProvider(LLMProvider):
    def __init__(self, response_text: str = "Mocked LLM answer"):
        self.response_text = response_text

    async def generate(self, prompt: str, system_prompt=None, model=None, temperature=0.3, max_tokens=2048):
        # Check if ship30 prompt
        if "Ship 30" in prompt or "atomic essay" in prompt:
            essay = """# The High Agency Playbook
High agency is the single most valuable trait in modern product management.
When constraints appear, low-agency people accept them as boundaries. Great builders find another path forward. Shreyas Doshi proved this at Stripe.
Here is why this matters now.

## 1. Re-Examine The Premise
- Never accept problems as handed down.
- Challenge assumptions before writing specs.

## 2. Eliminate The Feature Factory
Most PMs add complexity. Great PMs remove work and prune low-leverage features.

## Actionable Takeaway
Audit your product backlog tomorrow morning. Delete three features that do not directly move your core retention metric.

**Sources**: Shreyas Doshi on High Agency."""
            return LLMResponse(content=essay, model="mock-model", provider="mock")

        # Check if markdown artifact prompt
        if "markdown" in prompt.lower() and ("artifact" in prompt.lower() or "document" in prompt.lower()):
            md_art = """```markdown
# Product Strategy Specification

## Executive Summary
A comprehensive strategy document grounded in high agency leadership and cross-functional alignment.

## 1. Core Principles
- Crisp 1-pagers
- Detractor engagement
- Resourcefulness

## 2. Action Items
- Audit product backlog
- Streamline critical path
```"""
            return LLMResponse(content=md_art, model="mock-model", provider="mock")

        # Check if artifact prompt
        if "artifact" in prompt.lower() or "html" in prompt.lower():
            html_art = """```html
<!DOCTYPE html>
<html>
<head>
<title>Growth Funnel</title>
<style>body { background: #0B0F19; color: #fff; }</style>
</head>
<body>
<div class="card"><h1>Growth Funnel Dashboard</h1><p>Retention: 60%</p></div>
</body>
</html>
```"""
            return LLMResponse(content=html_art, model="mock-model", provider="mock")


        return LLMResponse(content=self.response_text, model="mock-model", provider="mock")

    async def is_available(self):
        return True

    async def get_models(self):
        return ["mock-model"]

@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    mock_prov = MockLLMProvider()
    provider_factory._providers["ollama"] = mock_prov
    provider_factory._providers["mock"] = mock_prov
    provider_factory.set_active_provider("mock")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
