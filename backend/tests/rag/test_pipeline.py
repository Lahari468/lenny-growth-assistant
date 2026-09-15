from pathlib import Path

from app.db.models import Document, DocumentChunk, EMBEDDING_DIMENSION
from app.rag.pipeline import TranscriptIngestionPipeline


def _write_transcript(directory: Path, filename: str, content: str) -> None:
    (directory / filename).write_text(content, encoding="utf-8")


EPISODE_A = (
    "---\n"
    'title: "Finding product-market fit"\n'
    'source_url: "https://www.lennysnewsletter.com/p/episode-a"\n'
    "published_at: 2024-01-15\n"
    'guest: "Jane Doe"\n'
    "---\n\n"
    "Lenny: Welcome to the show, Jane.\n"
    "Jane: Thanks for having me, excited to be here.\n"
    "Lenny: Let's start with how you define product-market fit.\n"
    "Jane: For me it's when growth stops being a struggle.\n"
)


def test_ingest_directory_inserts_document_and_chunks(tmp_path, db_session, fake_embedding_provider):
    _write_transcript(tmp_path, "episode-a.md", EPISODE_A)
    pipeline = TranscriptIngestionPipeline(embedding_provider=fake_embedding_provider)

    stats = pipeline.ingest_directory(tmp_path, db_session)

    assert stats.files_discovered == 1
    assert stats.documents_inserted == 1
    assert stats.documents_skipped == 0
    assert stats.chunks_created > 0

    document = db_session.query(Document).filter(Document.title == "Finding product-market fit").one()
    assert document.source_url == "https://www.lennysnewsletter.com/p/episode-a"

    chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()
    assert len(chunks) == stats.chunks_created
    assert all(len(c.embedding) == EMBEDDING_DIMENSION for c in chunks)


def test_ingest_directory_is_idempotent_for_unchanged_file(tmp_path, db_session, fake_embedding_provider):
    _write_transcript(tmp_path, "episode-a.md", EPISODE_A)
    pipeline = TranscriptIngestionPipeline(embedding_provider=fake_embedding_provider)

    first_stats = pipeline.ingest_directory(tmp_path, db_session)
    second_stats = pipeline.ingest_directory(tmp_path, db_session)

    assert first_stats.documents_inserted == 1
    assert second_stats.documents_inserted == 0
    assert second_stats.documents_updated == 0
    assert second_stats.documents_skipped == 1
    assert second_stats.chunks_created == 0

    # No duplicate documents or chunks were created.
    assert db_session.query(Document).count() == 1
    assert db_session.query(DocumentChunk).count() == first_stats.chunks_created


def test_ingest_directory_reindexes_when_content_changes(tmp_path, db_session, fake_embedding_provider):
    _write_transcript(tmp_path, "episode-a.md", EPISODE_A)
    pipeline = TranscriptIngestionPipeline(embedding_provider=fake_embedding_provider)
    pipeline.ingest_directory(tmp_path, db_session)

    original_document_id = db_session.query(Document).one().id

    updated_content = EPISODE_A + "Lenny: One more question before we wrap up.\n"
    _write_transcript(tmp_path, "episode-a.md", updated_content)

    stats = pipeline.ingest_directory(tmp_path, db_session)

    assert stats.documents_updated == 1
    assert stats.documents_inserted == 0
    assert stats.documents_skipped == 0

    # Same document row (same id), reused rather than duplicated.
    assert db_session.query(Document).count() == 1
    assert db_session.query(Document).one().id == original_document_id

    # Chunks were replaced, not appended to.
    chunks = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == original_document_id
    ).all()
    assert len(chunks) == stats.chunks_created
    all_content = " ".join(c.content for c in chunks)
    assert "One more question before we wrap up" in all_content


def test_chunks_are_traceable_to_their_source(tmp_path, db_session, fake_embedding_provider):
    _write_transcript(tmp_path, "episode-a.md", EPISODE_A)
    pipeline = TranscriptIngestionPipeline(embedding_provider=fake_embedding_provider)
    pipeline.ingest_directory(tmp_path, db_session)

    document = db_session.query(Document).one()
    chunks = (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )

    assert len(chunks) > 0
    for chunk in chunks:
        # Traceability required by spec: document_id, source_url, title,
        # chunk_index, and (when available) speaker metadata.
        assert chunk.document_id == document.id
        assert chunk.metadata_["source_url"] == "https://www.lennysnewsletter.com/p/episode-a"
        assert chunk.metadata_["title"] == "Finding product-market fit"
        assert isinstance(chunk.chunk_index, int)
        assert "speakers" in chunk.metadata_

    # At least one chunk should have captured a speaker name from the transcript.
    assert any(chunk.metadata_["speakers"] for chunk in chunks)


def test_ingest_directory_isolates_a_single_malformed_file(
    tmp_path, db_session, fake_embedding_provider
):
    _write_transcript(tmp_path, "good-episode.md", EPISODE_A)
    _write_transcript(tmp_path, "empty-episode.md", "---\ntitle: Empty\n---\n\n   \n")

    pipeline = TranscriptIngestionPipeline(embedding_provider=fake_embedding_provider)
    stats = pipeline.ingest_directory(tmp_path, db_session)

    assert stats.files_discovered == 2
    assert stats.documents_inserted == 1
    assert stats.documents_failed == 1
    # The good document still made it in despite the other file failing.
    assert db_session.query(Document).filter(Document.title == "Finding product-market fit").count() == 1


def test_embedding_failure_is_counted_and_does_not_abort_other_chunks(
    tmp_path, db_session, fake_embedding_provider
):
    # Long enough transcript to guarantee multiple chunks, so we can prove
    # one failed embedding doesn't take down the rest.
    long_body_lines = [
        f"Lenny: This is filler question number {i} to pad out the transcript nicely."
        if i % 2 == 0
        else f"Jane: This is filler answer number {i}, also padded out with extra words."
        for i in range(40)
    ]
    long_transcript = (
        "---\n"
        'title: "Long filler episode"\n'
        "---\n\n" + "\n".join(long_body_lines)
    )
    _write_transcript(tmp_path, "long-episode.md", long_transcript)

    calls = {"n": 0}
    original_embed = fake_embedding_provider.embed

    def flaky_embed(text: str):
        calls["n"] += 1
        if calls["n"] == 1:
            from app.rag.embeddings import EmbeddingError

            raise EmbeddingError("simulated embedding failure")
        return original_embed(text)

    fake_embedding_provider.embed = flaky_embed

    pipeline = TranscriptIngestionPipeline(embedding_provider=fake_embedding_provider)
    stats = pipeline.ingest_directory(tmp_path, db_session)

    assert calls["n"] > 1  # confirms multiple chunks were actually attempted
    assert stats.embedding_failures == 1
    assert stats.chunks_created == calls["n"] - 1  # every other chunk still stored
