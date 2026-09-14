"""
Developer verification CLI for the retrieval layer.

Usage:
    python -m app.rag.retrieve_test "your question here"
    python -m app.rag.retrieve_test --top-k 3 --threshold 0.5 "your question here"

This is a manual, human-in-the-loop debugging tool: it embeds a query with
the configured Ollama embedding model, runs it through the existing
Retriever (app.rag.retriever), and prints the results in a readable
format. It performs no writes of any kind — read-only against the
database. It is NOT a production API route; that's a separate, later
piece of work.

Requires a local Ollama server running with the configured embedding
model pulled (default: nomic-embed-text) and the database migrations
already applied.
"""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.rag.embeddings import EmbeddingError, OllamaEmbeddingProvider
from app.rag.retriever import RetrievalError, RetrievalValidationError, Retriever, RetrievedChunk

logger = logging.getLogger("app.rag.retrieve_test")

_PREVIEW_MAX_CHARS = 220


def _format_result(rank: int, result: RetrievedChunk) -> str:
    preview = " ".join(result.content.split())  # collapse newlines/whitespace
    if len(preview) > _PREVIEW_MAX_CHARS:
        preview = preview[:_PREVIEW_MAX_CHARS].rstrip() + "..."

    lines = [
        f"[{rank}] score={result.score:.4f}  distance={result.distance:.4f}",
        f"    Title:       {result.title}",
        f"    Source URL:  {result.source_url or '(none)'}",
        f"    Source file: {result.source_file or '(none)'}",
        f"    Chunk index: {result.chunk_index}",
    ]
    if result.speakers:
        lines.append(f"    Speakers:    {', '.join(result.speakers)}")
    if result.paragraph_start is not None or result.paragraph_end is not None:
        lines.append(f"    Paragraphs:  {result.paragraph_start} - {result.paragraph_end}")
    lines.append(f"    Preview:     {preview}")
    return "\n".join(lines)


def _print_results(query: str, results: list[RetrievedChunk]) -> None:
    if not results:
        print(f"No matching results for: {query!r}")
        return

    print(f"Top {len(results)} result(s) for: {query!r}\n")
    for rank, result in enumerate(results, start=1):
        print(_format_result(rank, result))
        print()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Developer utility: run a query through the RAG retriever and "
            "print the results. Read-only, never modifies the database."
        ),
        epilog=textwrap.dedent(
            """\
            Example:
                python -m app.rag.retrieve_test "how do I find product-market fit?"
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="The question to search for (wrap in quotes if it contains spaces).",
    )
    parser.add_argument(
        "--top-k",
        dest="top_k",
        type=int,
        default=5,
        help="Number of results to return (default: 5).",
    )
    parser.add_argument(
        "--threshold",
        dest="threshold",
        type=float,
        default=None,
        help="Optional minimum similarity score (0-1) to filter out low-relevance results.",
    )
    args = parser.parse_args(argv)

    query = " ".join(args.query).strip()

    settings = get_settings()
    embedding_provider = OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    )
    retriever = Retriever(embedding_provider=embedding_provider)

    db = SessionLocal()
    try:
        results = retriever.retrieve(
            query, db, top_k=args.top_k, similarity_threshold=args.threshold
        )
    except RetrievalValidationError as exc:
        logger.error(
            '%s Usage: python -m app.rag.retrieve_test "your question here"', exc
        )
        return 1
    except EmbeddingError as exc:
        logger.error("Ollama embedding backend unavailable: %s", exc)
        return 1
    except RetrievalError as exc:
        # RetrievalError's message is already generic and safe to print
        # (see app.rag.retriever) — it never includes connection details.
        logger.error(str(exc))
        return 1
    finally:
        db.close()

    _print_results(query, results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
