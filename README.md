# Lenny Growth Assistant

**Built by Jaya Lahari Kadiyala**

A transcript-grounded product intelligence assistant for product managers, growth teams, and founders.

Lenny Growth Assistant combines retrieval, source-grounded answers, local LLM inference, conversation history, and an artifact workspace in one focused product workflow.

## What it does

### 1. Grounded Product & Growth Q&A
Ask questions about product strategy, growth, activation, retention, PMF, founder mode, and related topics. The assistant retrieves relevant knowledge-base chunks and attaches source information to the response.

### 2. Evidence-first answers
The assistant is designed not to guess when the available knowledge base does not support a question. Unsupported questions receive an insufficient-evidence response instead of an invented answer.

### 3. Ship 30
Turn a grounded product/growth insight into a longer-form, structured piece of writing while preserving source markers.

### 4. Artifact workspace
Generate Markdown/HTML-style artifacts and inspect them beside the conversation without leaving the main workflow.

### 5. Independent conversations
Each conversation has its own session and message history.

## Tech stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** FastAPI, Python
- **Database:** PostgreSQL
- **Vector search:** pgvector
- **Local inference:** Ollama
- **Models used in the local demo:** `nomic-embed-text`, `phi3:latest`, `llama3:latest`
- **API documentation:** FastAPI / OpenAPI
- **Testing:** pytest

## Architecture

```text
User
  ↓
React + TypeScript UI
  ↓
FastAPI API
  ├── Session / message persistence
  ├── Retrieval service
  ├── pgvector similarity search
  ├── Grounded answer generation
  ├── Ship 30 skill
  └── Artifact generation
        ↓
PostgreSQL + pgvector
        ↓
Ollama
  ├── nomic-embed-text
  └── phi3 / llama3
```

## Knowledge base

The repository includes a small **demo knowledge base** in:

```text
data/transcripts/
```

The JSON fixtures use the schema expected by the ingestion pipeline.

Important: the bundled content is **original paraphrased demonstration material**, not a verbatim redistribution of Lenny's Podcast transcripts. The source metadata is retained for traceability.

See:

- `docs/transcript-sources.md`
- `data/transcripts/README.md`
- `docs/knowledge-base.md`

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Ollama

Make sure Ollama is installed and the required local models are available:

```bash
ollama list
ollama pull nomic-embed-text
ollama pull phi3
ollama pull llama3
```

If Ollama is already running, do not start a second server.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` requests to:

```text
http://localhost:8000
```

## Useful checks

Backend health:

```bash
curl http://127.0.0.1:8000/api/health
```

Available models:

```bash
curl http://127.0.0.1:8000/api/models
```

Frontend:

```text
http://localhost:5173
```

## Demo flow

1. Open the application.
2. Ask a grounded product-growth question.
3. Show the answer and source evidence.
4. Start a new conversation.
5. Generate a Ship 30 artifact.
6. Generate an HTML/product-growth artifact.
7. Show the Artifact Viewer.
8. Demonstrate the insufficient-evidence behavior with an unrelated question.

Recommended demo question:

> What are the most important lessons about product growth?

Recommended artifact prompt:

> Create an HTML dashboard showing activation, retention, conversion, and engagement metrics.

## Project documentation

| File | Purpose |
|---|---|
| `docs/PRD.md` | Product requirements and acceptance criteria |
| `docs/design.md` | UI/UX and interaction decisions |
| `docs/architecture.md` | Technical architecture |
| `docs/transcript-sources.md` | Source and traceability policy |
| `docs/knowledge-base.md` | Included knowledge-base fixtures |
| `docs/manual-test-plan.md` | Manual verification steps |
| `docs/agent-transcripts/` | Development/debugging record |

## Repository hygiene

Do not commit:

```text
.env
.venv/
node_modules/
dist/
__pycache__/
*.db
```

Use `.env.example` as the public configuration template.

---

**Author:** Jaya Lahari Kadiyala  
**Project:** Lenny Growth Assistant  
**Purpose:** Product-growth assistant / RAG take-home project
