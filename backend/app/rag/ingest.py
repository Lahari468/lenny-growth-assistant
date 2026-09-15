"""
CLI entry point for transcript ingestion.

Usage:
    python -m app.rag.ingest
    python -m app.rag.ingest --dir /custom/path/to/transcripts

Requires a local Ollama server running with the configured embedding
model pulled (default: nomic-embed-text). Requires the database
migrations to already be applied (see alembic).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.rag.embeddings import EmbeddingError, OllamaEmbeddingProvider
from app.rag.pipeline import TranscriptDirectoryNotFoundError, TranscriptIngestionPipeline

# Project root is the parent of backend/ (this file lives at
# backend/app/rag/ingest.py).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_transcripts_dir(cli_dir: str | None) -> Path:
    settings = get_settings()
    raw = cli_dir or settings.transcripts_dir
    path = Path(raw)
    return path if path.is_absolute() else _PROJECT_ROOT / path


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )
    logger = logging.getLogger("app.rag.ingest")

    parser = argparse.ArgumentParser(description="Ingest podcast transcripts into the RAG store.")
    parser.add_argument(
        "--dir",
        dest="dir",
        default=None,
        help="Path to the transcripts directory (defaults to TRANSCRIPTS_DIR setting).",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    directory = _resolve_transcripts_dir(args.dir)

    embedding_provider = OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    )
    pipeline = TranscriptIngestionPipeline(embedding_provider=embedding_provider)

    db = SessionLocal()
    try:
        pipeline.ingest_directory(directory, db)
        return 0
    except TranscriptDirectoryNotFoundError as exc:
        logger.error(str(exc))
        return 1
    except EmbeddingError as exc:
        logger.error("Ollama embedding backend unavailable: %s", exc)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
