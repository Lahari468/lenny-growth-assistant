# Transcript / Knowledge-Source Manifest

## Project owner

**Jaya Lahari Kadiyala**

## Purpose

Lenny Growth Assistant uses a small, traceable knowledge base to demonstrate RAG behavior.

The public repository deliberately distinguishes between:

1. permitted verbatim transcript material, if the repository owner has redistribution rights; and
2. original paraphrased demo notes used to test retrieval and grounding.

The bundled fixtures in `data/transcripts/` belong to the second category.

## Included demonstration sources

The current fixtures cover these source topics:

- Shreyas Doshi — high agency and product work
- Elena Verna — product-led growth and activation
- Brian Chesky — founder mode and product quality
- Gustaf Alström­er — retention and growth
- Casey Winters — growth loops and retention

The JSON files contain paraphrased notes and must not be described as verbatim transcripts.

## Traceability

Each fixture stores:

- document ID;
- title;
- guest;
- source URL;
- publication date where available;
- knowledge-base content.

The application can therefore trace:

```text
answer
→ source marker
→ retrieved chunk
→ document
→ source metadata
```

## Adding an authorized transcript

If an authorized transcript is available:

1. place it under `data/transcripts/`;
2. preserve title, guest, URL, and date metadata;
3. confirm redistribution rights;
4. run ingestion;
5. test a question that should retrieve the new material;
6. verify that the UI source card points to the correct source.

Never invent a source URL or label paraphrased notes as a real transcript.
