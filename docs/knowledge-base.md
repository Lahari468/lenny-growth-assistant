# Knowledge Base — Lenny Growth Assistant

## Purpose

This directory documents the small demonstration corpus bundled with the project.

The corpus is designed to demonstrate:

- semantic retrieval;
- source traceability;
- grounded answering;
- insufficient-evidence behavior;
- artifact generation from retrieved context.

## Included topics

| Fixture | Topic |
|---|---|
| `shreyas-doshi-high-agency-pm.json` | High agency, problem framing, persuasion, product work |
| `elena-verna-plg-and-growth.json` | Product-led growth, activation, time-to-value |
| `brian-chesky-founder-mode.json` | Founder mode, product quality, design reviews |
| `gustaf-alstromer-yc-growth.json` | Retention curves, North Star metrics, growth |
| `casey-winters-retention-loops.json` | Growth loops, retention, compounding systems |

## Content policy

The included JSON files contain **original paraphrased demo notes**. They are not presented as official verbatim podcast transcripts.

The files preserve source metadata so the application can demonstrate a traceability chain:

```text
user question
  ↓
retrieved chunk
  ↓
source metadata
  ↓
grounded answer
  ↓
citation/source card
```

Do not add copyrighted transcript text to a public repository unless you have permission to redistribute it.

## JSON format

Each fixture follows the application's ingestion contract:

```json
{
  "id": "unique-document-id",
  "title": "Document title",
  "guest": "Guest name",
  "source_url": "https://...",
  "published_at": "YYYY-MM-DD",
  "content": "Original paraphrased source notes..."
}
```
