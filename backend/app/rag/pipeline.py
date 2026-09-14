"""
Transcript ingestion pipeline.

Orchestrates: load -> normalize -> chunk -> embed -> store document ->
store chunks, for every supported file under a transcripts directory.

Idempotency:
- Each file is identified by its path relative to the transcripts
  directory (stored as `source_file` in the document's metadata), not by
  source_url, since source_url is optional.
- A SHA-256 hash of the normalized transcript body is stored alongside it.
  Re-running ingestion on an unchanged file updates the document's
  metadata (cheap) but skips re-chunking and re-embedding entirely.
- If the body changed, existing chunks for that document are deleted and
  replaced with freshly embedded ones — same document row, new chunks.

Error isolation: a failure loading, parsing, or embedding one file is
logged and counted, and ingestion continues with the remaining files
(see `_ingest_file`). A completely unreachable embedding backend is
different: every subsequent embedding call would fail identically, so
that is checked once up front and aborts the whole run with a clear error
instead of failing file-by-file.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.rag.chunker import chunk_transcript
from app.rag.embeddings import EmbeddingError, EmbeddingProvider
from app.rag.loader import TranscriptLoadError, discover_transcript_files, load_transcript_file
from app.rag.normalize import normalize_whitespace, split_paragraphs

logger = logging.getLogger("app.rag.ingest")


class TranscriptDirectoryNotFoundError(RuntimeError):
    """Raised when the configured transcripts directory doesn't exist."""


@dataclass
class IngestionStats:
    files_discovered: int = 0
    documents_inserted: int = 0
    documents_updated: int = 0
    documents_skipped: int = 0
    documents_failed: int = 0
    chunks_created: int = 0
    embedding_failures: int = 0
    duration_seconds: float = 0.0


class TranscriptIngestionPipeline:
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider

    def ingest_directory(self, directory: Path, db: Session) -> IngestionStats:
        start = time.monotonic()
        stats = IngestionStats()

        if not directory.exists() or not directory.is_dir():
            raise TranscriptDirectoryNotFoundError(
                f"Transcript directory not found: {directory}"
            )

        files = discover_transcript_files(directory)
        stats.files_discovered = len(files)
        logger.info("Discovered %d transcript file(s) in %s", len(files), directory)

        if files:
            # Fail fast on a completely unreachable embedding backend
            # rather than failing identically on every single file.
            try:
                self.embedding_provider.health_check()
            except EmbeddingError as exc:
                logger.error("Embedding provider unavailable, aborting: %s", exc)
                raise

        for path in files:
            try:
                self._ingest_file(path, directory, db, stats)
            except TranscriptLoadError as exc:
                stats.documents_failed += 1
                logger.error("Skipping malformed file %s: %s", path.name, exc)
                db.rollback()
            except Exception as exc:  # noqa: BLE001 - one bad file must not abort the run
                stats.documents_failed += 1
                logger.error("Unexpected error ingesting %s: %s", path.name, exc)
                db.rollback()

        stats.duration_seconds = time.monotonic() - start
        logger.info(
            "Ingestion complete: %d inserted, %d updated, %d skipped, %d failed, "
            "%d chunks created, %d embedding failures, %.2fs",
            stats.documents_inserted,
            stats.documents_updated,
            stats.documents_skipped,
            stats.documents_failed,
            stats.chunks_created,
            stats.embedding_failures,
            stats.duration_seconds,
        )
        return stats

    def _ingest_file(
        self, path: Path, base_dir: Path, db: Session, stats: IngestionStats
    ) -> None:
        raw = load_transcript_file(path, base_dir)
        normalized_body = normalize_whitespace(raw.body)
        content_hash = hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()

        document = (
            db.query(Document)
            .filter(Document.metadata_["source_file"].astext == raw.source_file)
            .one_or_none()
        )

        metadata = dict(raw.extra_metadata)
        metadata["source_file"] = raw.source_file
        metadata["content_hash"] = content_hash

        is_new = document is None
        if is_new:
            document = Document(
                title=raw.title,
                source_url=raw.source_url,
                published_at=raw.published_at,
                metadata_=metadata,
            )
            db.add(document)
            db.flush()  # assign document.id for use by chunks below
            needs_reindex = True
        else:
            previous_hash = (document.metadata_ or {}).get("content_hash")
            needs_reindex = previous_hash != content_hash
            document.title = raw.title
            document.source_url = raw.source_url
            document.published_at = raw.published_at
            document.metadata_ = metadata

        if not needs_reindex:
            db.commit()
            stats.documents_skipped += 1
            logger.info("Skipped (unchanged): %s", raw.source_file)
            return

        paragraphs = split_paragraphs(normalized_body)
        chunk_defs = chunk_transcript(paragraphs)

        if not is_new:
            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document.id
            ).delete()
            db.flush()

        created = 0
        for chunk in chunk_defs:
            try:
                embedding = self.embedding_provider.embed(chunk.content)
            except EmbeddingError as exc:
                stats.embedding_failures += 1
                logger.error(
                    "Embedding failed for %s chunk %d: %s",
                    raw.source_file,
                    chunk.chunk_index,
                    exc,
                )
                continue

            chunk_metadata = dict(chunk.metadata)
            chunk_metadata.update(
                {
                    "source_file": raw.source_file,
                    "source_url": raw.source_url,
                    "title": raw.title,
                }
            )
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    embedding=embedding,
                    metadata_=chunk_metadata,
                )
            )
            created += 1

        db.commit()
        stats.chunks_created += created

        if is_new:
            stats.documents_inserted += 1
            logger.info("Inserted %s (%d chunks)", raw.source_file, created)
        else:
            stats.documents_updated += 1
            logger.info("Re-indexed %s (%d chunks)", raw.source_file, created)
