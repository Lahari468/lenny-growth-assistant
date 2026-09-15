"""
Transcript ingestion pipeline for The Lenny Growth Assistant.
Processes raw transcripts from data/transcripts/, cleans text, chunks with overlap,
computes vector embeddings, and stores idempotently in PostgreSQL / SQLite.
"""

import os
import sys
import json
import glob
import uuid
import logging
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))


from app.db.database import init_db, get_session_factory
from app.db.models import TranscriptModel, TranscriptChunkModel
from app.retrieval.embeddings import get_embedding_engine
from sqlalchemy import select, delete

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest")

CHUNK_SIZE = 2500       # Approximately 500-750 tokens
CHUNK_OVERLAP = 400     # Approximately 100 tokens

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Chunk text into 500-800 token segments with overlap, breaking at sentences."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # Look for sentence boundary near end
            last_period = text.rfind(". ", start, end)
            if last_period != -1 and last_period > start + chunk_size // 2:
                end = last_period + 1

        chunk_slice = text[start:end].strip()
        if chunk_slice:
            chunks.append(chunk_slice)

        if end >= text_len:
            break

        start = max(start + 1, end - overlap)

    return chunks


async def run_ingestion():
    logger.info("Initializing database connection for transcript ingestion...")
    await init_db()

    embedding_engine = get_embedding_engine()
    transcripts_dir = PROJECT_ROOT / "data" / "transcripts"
    transcript_files = glob.glob(str(transcripts_dir / "*.json"))

    if not transcript_files:
        logger.error("No transcript files found in %s", transcripts_dir)
        return

    logger.info("Discovered %d transcript files in %s", len(transcript_files), transcripts_dir)

    session_factory = get_session_factory()
    assert session_factory is not None, "Database session factory is not initialized"
    async with session_factory() as db:
        total_chunks_ingested = 0


        for file_path in transcript_files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            t_id = data["id"]
            title = data["title"]
            guest = data["guest"]
            source_url = data["source_url"]
            published_at = data.get("published_at")
            content = data["content"]

            logger.info("Processing: '%s' (Guest: %s)", title, guest)

            # Upsert transcript record
            existing_t = await db.get(TranscriptModel, t_id)
            if not existing_t:
                transcript_model = TranscriptModel(
                    id=t_id,
                    title=title,
                    guest=guest,
                    source_url=source_url,
                    published_at=published_at,
                    content=content,
                )
                db.add(transcript_model)
            else:
                existing_t.title = title
                existing_t.guest = guest
                existing_t.source_url = source_url
                existing_t.published_at = published_at
                existing_t.content = content

            # Remove old chunks for idempotency
            await db.execute(delete(TranscriptChunkModel).where(TranscriptChunkModel.transcript_id == t_id))

            # Generate chunks
            chunks = chunk_text(content)
            logger.info("Generated %d chunks for transcript '%s'", len(chunks), t_id)

            for idx, chunk_content in enumerate(chunks):
                # Generate deterministic chunk id
                chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{t_id}-chunk-{idx}"))
                embedding_vector = embedding_engine.embed_text(chunk_content)

                metadata = {
                    "transcript_id": t_id,
                    "guest": guest,
                    "title": title,
                    "source_url": source_url,
                    "chunk_index": idx,
                }

                chunk_record = TranscriptChunkModel(
                    id=chunk_uuid,
                    transcript_id=t_id,
                    chunk_index=idx,
                    content=chunk_content,
                    embedding_json=json.dumps(embedding_vector),
                    metadata_json=json.dumps(metadata),
                )
                db.add(chunk_record)
                total_chunks_ingested += 1

            await db.commit()

        logger.info("Ingestion completed successfully! Total chunks indexed: %d", total_chunks_ingested)

if __name__ == "__main__":
    asyncio.run(run_ingestion())
