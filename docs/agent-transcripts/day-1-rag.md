# Day 1 — RAG Foundation

## Objective

Build the backend foundation required for a transcript-grounded assistant.

## Work completed

- FastAPI project foundation
- PostgreSQL schema
- pgvector integration
- Alembic migrations
- User/session/message/document/chunk models
- Transcript loader
- Normalization
- Chunking
- Embeddings
- Ingestion
- Retrieval
- Retrieval traceability
- Automated tests

## Verification

The database and retrieval foundation was exercised through automated tests and a retrieval test CLI.

## Correction / Lesson

The local PostgreSQL role differed from the default `postgres` assumption. The configuration was corrected to use the local development role rather than hard-coding an environment-specific database user.

## Engineering principle

Infrastructure assumptions should be configurable and verified against the actual local environment.
