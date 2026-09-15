"""
Retrieval & Vector Search Tests.
Verifies cosine similarity, chunk relevance, metadata preservation, and no-result refusal behavior.
"""

import pytest
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import TranscriptModel, TranscriptChunkModel
from app.retrieval.vector_store import vector_store, cosine_similarity
from app.retrieval.embeddings import get_embedding_engine

@pytest.mark.asyncio
async def test_cosine_similarity_math():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 0.01) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v3), 0.01) == 0.0

@pytest.mark.asyncio
async def test_retrieval_and_metadata_preservation(test_db: AsyncSession):
    engine = get_embedding_engine()
    
    # Insert test transcript and chunk
    t = TranscriptModel(
        id="test-shreyas",
        title="High Agency Product Management",
        guest="Shreyas Doshi",
        source_url="https://lennyspodcast.com/test-shreyas",
        content="Shreyas Doshi explains high agency and problem framing for PMs.",
    )
    test_db.add(t)

    chunk_vec = engine.embed_text("High agency product managers refuse to accept obstacles.")
    chunk = TranscriptChunkModel(
        id="chunk-1",
        transcript_id="test-shreyas",
        chunk_index=0,
        content="High agency product managers refuse to accept obstacles and find a way forward.",
        embedding_json=json.dumps(chunk_vec),
        metadata_json=json.dumps({"topic": "agency"}),
    )
    test_db.add(chunk)
    await test_db.commit()

    # Search query
    results = await vector_store.search(test_db, query="high agency PM obstacles", top_k=2)
    assert len(results) > 0
    top = results[0]
    assert top.guest == "Shreyas Doshi"
    assert top.episode_title == "High Agency Product Management"
    assert top.source_url == "https://lennyspodcast.com/test-shreyas"
    assert top.similarity_score > 0.3

@pytest.mark.asyncio
async def test_empty_retrieval_behavior(test_db: AsyncSession):
    # Search on empty database should return empty list without crashing
    results = await vector_store.search(test_db, query="quantum entanglement astrophysics", min_similarity=0.9)
    assert len(results) == 0
