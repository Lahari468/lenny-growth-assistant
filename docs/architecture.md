# Architecture — Lenny Growth Assistant

## 1. Architectural goal

Keep the application modular enough that retrieval, provider selection, session persistence, writing skills, and artifact rendering can evolve independently.

## 2. Topology

```text
+-----------------------------+
| React + TypeScript frontend |
| Chat / Sources / Artifacts  |
+-------------+---------------+
              |
              | HTTP/JSON
              v
+-----------------------------+
| FastAPI API                 |
| sessions / chat / health    |
+------+------+---------------+
       |      |
       |      +--------------------+
       |                           |
       v                           v
+--------------+            +-------------+
| Session / DB |            | Agent /     |
| services     |            | skills      |
+------+-------+            +------+------+
       |                           |
       v                           v
+---------------------------------------------+
| PostgreSQL + pgvector                       |
| sessions / users / messages / documents /   |
| document_chunks / embeddings                |
+-------------------+-------------------------+
                    |
                    v
             +-------------+
             | RAG layer   |
             | embeddings  |
             | retrieval   |
             +------+------+ 
                    |
                    v
             +-------------+
             | Transcript  |
             | corpus      |
             +-------------+

Provider boundary:
FastAPI/services -> ChatProvider -> Ollama | Anthropic
```

## 3. Backend boundaries

### `app/api`

HTTP contracts, validation, status codes, and serialization.

Key routes:

- `/api/health`
- `/api/sessions`
- `/api/sessions/{session_id}`
- `/api/sessions/{session_id}/messages`
- `/api/chat/grounded`
- `/api/chat/ship30`

### `app/rag`

Responsible for:

- transcript discovery;
- normalization;
- hashing/idempotency;
- chunking;
- embeddings;
- retrieval;
- source traceability;
- grounded answer construction.

RAG code does not own HTTP behavior.

### `app/providers`

The provider contract hides model-specific HTTP/SDK behavior.

Implementations include:

- Ollama;
- Anthropic.

The application selects a provider through configuration or explicit request override.

### `app/services`

Business workflows that combine retrieval, provider calls, persistence, and skill validation.

`Ship30Skill` lives here because it is a distinct product capability.

### `app/agents`

The Pi bridge provides the agent/orchestration boundary used by session chat. The grounded answerer remains the source-of-truth for transcript grounding.

The current Docker demo intentionally tolerates Pi executable absence and falls back to the deterministic grounded service. This is logged as an operational condition rather than hidden.

## 4. Data model

### Users

Stores user metadata used by sessions.

### Chat sessions

- UUID
- user reference
- title
- provider
- created timestamp
- updated timestamp

### Messages

- UUID
- session reference
- role
- content
- provider
- model
- created timestamp

### Documents

Stores source metadata and content hash.

### Document chunks

Stores:

- document reference
- chunk index
- content
- vector embedding
- source file
- source URL
- speakers
- paragraph range

### Artifacts

Stores generated Markdown/HTML artifact metadata and content where supported by the current artifact implementation.

## 5. Retrieval flow

```text
User question
    |
    v
Ollama embedding model
    |
    v
query vector
    |
    v
pgvector cosine similarity
    |
    v
top-k + similarity threshold
    |
    v
RetrievedChunk[]
    |
    +--> source metadata
    |
    v
grounded prompt
    |
    v
selected provider
    |
    v
answer
    |
    v
citation validation
    |
    v
UI + sources
```

The embedding model is always separate from the chat model.

## 6. Ingestion and refresh

The ingestion command is:

```bash
docker compose exec backend python -m app.rag.ingest
```

It is designed to be idempotent.

Unchanged source files are skipped. Changed files are reprocessed.

The Docker mount makes the host corpus available at:

```text
/data/transcripts
```

## 7. Session isolation

The session ID is the boundary for conversation persistence.

Message writes require an existing session.

An invalid UUID/session produces `404 Session not found`.

The frontend removes a stale browser session when restoration fails and creates a new session on the next request.

## 8. Provider selection

```text
                    +----------------+
                    | Provider config|
                    +-------+--------+
                            |
             +--------------+--------------+
             |                             |
             v                             v
       Ollama provider              Anthropic provider
       local / demo                 cloud / optional
```

Normal chat uses the configured default timeout.

Ship 30 passes an explicit longer timeout because the expected response is long-form.

## 9. Ship 30 architecture

```text
Topic
  |
  v
Retriever
  |
  v
Evidence with [S1], [S2], ...
  |
  v
Ship30Skill.build_prompt()
  |
  v
ChatProvider.generate()
  |
  v
Length + citation validation
  |
  v
Markdown artifact response
```

The validator rejects:

- empty content;
- essays below the minimum practical range;
- essays above the maximum range;
- unsupported source markers;
- essays without citations when evidence is present.

## 10. Security

Generated HTML is untrusted.

The intended defense-in-depth model is:

```text
generated HTML
      |
      v
server-side sanitization
      |
      v
isolated iframe
      |
      v
no script execution / no parent DOM access
```

Chat responses should not use unsafe HTML injection.

## 11. Observability

Logs include safe operational fields such as:

- provider;
- model;
- request path;
- retrieval count;
- similarity/relevance;
- duration;
- success/failure class.

Secrets, credentials, full prompts, and transcript payloads should not be logged.

## 12. Deployment topology

Docker Compose runs:

1. `db` — PostgreSQL + pgvector;
2. `backend` — FastAPI + migrations;
3. `frontend` — built React app served by Nginx.

Ollama remains on the host because the assignment's local-model demo is performed with the host's Ollama runtime. The backend reaches it through Docker's `host.docker.internal`.

## 13. Important trade-offs

### pgvector inside PostgreSQL

One datastore reduces operational complexity for a small corpus.

### Local Ollama

It satisfies the mandatory demo requirement and avoids cloud dependency, at the cost of higher local latency.

### Thin agent boundary

The agent layer is kept small so grounding logic remains deterministic and testable.

### Source traceability over opaque answers

Every retrieved chunk carries source metadata so the UI can show why an answer was produced.
