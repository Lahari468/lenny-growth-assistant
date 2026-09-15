# Lenny Growth Assistant — Knowledge Base

This folder contains the small demonstration corpus used by the RAG pipeline.

## Current files

- `shreyas-doshi-high-agency-pm.json`
- `elena-verna-plg-and-growth.json`
- `brian-chesky-founder-mode.json`
- `gustaf-alstromer-yc-growth.json`
- `casey-winters-retention-loops.json`

## Important

The included `content` fields are **original paraphrased demonstration notes**.

They are not official verbatim Lenny's Podcast transcripts and should not be represented as such.

## JSON schema

```json
{
  "id": "document-id",
  "title": "Document title",
  "guest": "Guest name",
  "source_url": "https://...",
  "published_at": "YYYY-MM-DD",
  "content": "Paraphrased source notes"
}
```

## Ingestion

Use the ingestion command documented by the backend.

For a Docker-based setup:

```bash
docker compose exec backend python -m app.rag.ingest
```

For a local Python setup, use the ingestion entry point exposed by the project.

After ingestion, test a question whose answer should be supported by one of the included topics.
