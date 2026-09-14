# Lenny Growth Assistant

> A grounded, full-stack AI assistant for product and growth questions over Lenny's Podcast transcripts.

## Assessment Context

This project is being built as a Forward Deployed Engineer take-home assignment. The product goal is to turn a transcript knowledge base into a reliable internal assistant that can answer product/growth questions, preserve independent conversation context, generate reusable content, and render artifacts inside the application.

The implementation is intentionally developed in vertical slices. Documentation distinguishes implemented capabilities from planned work so an evaluator can reproduce the current state accurately.

## Current Status

### Implemented

- FastAPI backend foundation
- PostgreSQL persistence
- pgvector-based vector storage
- Transcript loading, normalization, chunking, and ingestion pipeline
- Content-hash/source-based ingestion idempotency
- Ollama `nomic-embed-text` embeddings
- Ollama chat provider using configurable `phi3:latest`
- Provider abstraction for future cloud/local model switching
- pgvector cosine-similarity retrieval
- Retrieval source traceability
- Grounded answer generation with `[S1]`, `[S2]`-style source citations
- Deterministic insufficient-context behavior when retrieval returns no evidence
- Provider and RAG automated tests
- Safe structured logging that avoids logging raw user queries, transcript content, or generated answers

### In Progress

- Agent layer using the required Anthropic Claude Agent SDK or Pi Coding Agent
- Independent chat-session API and message persistence
- Ship 30 for 30 content skill
- Artifact generation and in-app artifact viewer
- React frontend
- Docker Compose / reproducible one-command startup
- Final cloud-provider configuration and UI model/provider toggle
- Final end-to-end and fresh-clone verification

## Product

### Primary user

The primary user is a product or growth practitioner who wants to quickly extract practical lessons from Lenny's Podcast transcripts without manually searching long-form conversations.

### Core job

> "Help me answer a product/growth question using the relevant ideas from Lenny's content, show me where the answer came from, and turn the result into something I can reuse."

### Problem

Transcript repositories contain valuable product knowledge but are difficult to search conversationally. A user should not need to understand embeddings, vector databases, model providers, or prompting to get a trustworthy answer.

## Architecture Overview

```text
User
  |
  v
React Web App
  |
  v
FastAPI API
  |
  +--------------------+
  |                    |
  v                    v
Session/Chat API     Agent Layer
  |                    |
  v                    v
PostgreSQL          RAG / Skills / Tools
  |                    |
  +----------+---------+
             |
             v
      pgvector Retrieval
             |
             v
      Transcript Chunks
             |
             v
      LLM Provider Layer
        /           \
   Ollama           Cloud LLM
```

The current backend foundation already implements the retrieval and grounded-answer portions of this architecture. Agent orchestration and the user-facing product layer are the next vertical slices.

## Knowledge Base Pipeline

```text
Transcript files
      |
      v
Load
      |
      v
Normalize
      |
      v
Chunk
      |
      v
Embed with nomic-embed-text
      |
      v
Store in PostgreSQL + pgvector
      |
      v
Query embedding
      |
      v
Cosine similarity retrieval
      |
      v
Grounded context
      |
      v
Answer with source citations
```

Each retrieved source is traceable back to its stored document/chunk metadata. Ingestion is designed to be idempotent so repeated refreshes do not unnecessarily duplicate existing content.

## Repository Structure

```text
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── providers/
│   │   └── rag/
│   └── tests/
├── data/
│   └── transcripts/
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   ├── design.md
│   ├── manual-test-plan.md
│   └── agent-transcripts/
├── README.md
└── .env.example
```

## Technology

| Layer | Technology |
|---|---|
| API | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| Vector search | pgvector |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Embeddings | Ollama `nomic-embed-text` |
| Local chat model | Ollama `phi3:latest` |
| Validation/config | Pydantic / pydantic-settings |
| Testing | pytest |
| Frontend | React + TypeScript (planned/current integration stage) |
| Agent | Anthropic Claude Agent SDK or Pi Coding Agent (required integration) |

## Prerequisites

- Python 3.11+ recommended
- PostgreSQL with pgvector
- Ollama
- Git
- Node.js/npm once the frontend is enabled

## Local Model Setup

Verify Ollama is available:

```bash
curl http://localhost:11434/api/tags
```

Required local models:

```bash
ollama pull nomic-embed-text
ollama pull phi3:latest
```

If `ollama serve` reports that port `11434` is already in use, an Ollama server is likely already running. Do not start a second server; verify it with the curl command above.

## Environment Configuration

Copy the example configuration:

```bash
cp .env.example .env
```

Use a local PostgreSQL role/database appropriate to your machine. Do not commit `.env`.

Typical local configuration includes:

```env
DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/lenny_growth_assistant
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=phi3:latest
```

Embedding configuration should remain independent from the chat provider so changing the chat model does not change vector dimensions or invalidate the knowledge base.

## Database

Create the database and ensure pgvector is installed/enabled.

Run migrations from the backend according to the Alembic configuration:

```bash
alembic upgrade head
```

Verify the schema:

```bash
psql -d lenny_growth_assistant -c "\dt"
```

## Running the Backend

From `backend/`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The exact application import path should be verified against the current `app/main.py` before a fresh-clone submission.

## Transcript Ingestion

Transcript data is stored under the repository-level:

```text
data/transcripts/
```

The ingestion flow loads transcript files, normalizes their content, creates deterministic chunks, generates embeddings, and persists documents/chunks with source metadata.

Before final submission, verify the configured transcript path works from a fresh clone. The repository currently keeps transcript data at the root-level `data/transcripts/`, rather than under `backend/data/transcripts/`.

## Testing

Run the backend test suite:

```bash
pytest -q
```

The current development baseline reached **80 passing tests** after the provider and grounded-answer work. The final submission must rerun the complete suite after all remaining features are implemented.

Tests currently cover provider behavior and grounded-answer/RAG behavior, in addition to the existing backend foundation.

## Grounding Behavior

The assistant should never fabricate an answer when the transcript knowledge base does not provide sufficient evidence.

The current grounded-answer layer:

1. Retrieves relevant chunks.
2. Assigns source IDs such as `[S1]`.
3. Places only retrieved transcript evidence into the model context.
4. Instructs the model to answer from that evidence.
5. Returns a deterministic insufficient-context message when retrieval returns no chunks.
6. Sanitizes citations so the response cannot claim sources that were not supplied.

This is a deliberate product decision: a concise "the available transcripts do not support this" response is preferable to a plausible but unsupported answer.

## Reliability and Failure Handling

Important failure modes include:

- PostgreSQL unavailable
- pgvector unavailable
- Ollama unavailable
- Ollama model missing
- Model timeout
- Empty retrieval result
- Invalid model citations
- Missing environment configuration

The provider and RAG layers use bounded timeouts, structured errors, and safe logging. The final API layer will expose these failures as stable structured responses rather than leaking internal stack traces.

## Security

- Secrets belong in `.env`, never in Git.
- Logs must not contain raw transcript content, user prompts, or generated answers.
- User/session boundaries must be enforced server-side.
- Generated HTML is treated as untrusted content.
- The artifact viewer must isolate or sanitize generated HTML before rendering.
- Database queries must remain parameterized through the application data layer.
- The final application should avoid exposing provider credentials to the browser.

## Design Principles

1. **Ground before generating.**
2. **Make uncertainty visible.**
3. **Keep conversations isolated.**
4. **Prefer a small reliable architecture over unnecessary agent complexity.**
5. **Make provider selection explicit.**
6. **Design for evaluator handoff.**
7. **Treat generated artifacts as untrusted.**

## Known Limitations at This Stage

The repository is not yet the final assessment build. The required agent integration, frontend, artifact viewer, Ship 30 skill, Docker startup, and final cloud-provider path are still being completed.

This status is intentionally explicit so the documentation does not overstate the implementation.

## Final Verification Checklist

Before submission:

- [ ] Fresh clone works without local-only assumptions.
- [ ] `.env.example` is complete and contains no secrets.
- [ ] PostgreSQL + pgvector setup is documented.
- [ ] Ollama setup works on a clean machine.
- [ ] Transcript ingestion works from the documented path.
- [ ] Agent SDK/Pi integration is real and tested.
- [ ] Sessions are independent and persisted.
- [ ] Follow-up questions retain session context.
- [ ] Unsupported questions produce grounded insufficient-context behavior.
- [ ] Ship 30 output meets the required writing constraints.
- [ ] Artifact viewer renders safely.
- [ ] HTML artifacts are isolated/sanitized.
- [ ] Provider selection is visible/configurable.
- [ ] Automated tests pass.
- [ ] Manual UI test plan passes.
- [ ] Agent transcripts are sanitized.
- [ ] Demo video is recorded with camera enabled.
- [ ] Public GitHub repository contains no secrets.
