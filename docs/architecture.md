# Architecture — Lenny Growth Assistant

## 1. Architectural Goal

Provide a modular full-stack application where the conversational agent can combine session context, transcript retrieval, model providers, writing skills, and artifact generation while keeping infrastructure concerns isolated.

## 2. High-Level Topology

```text
                 +----------------------+
                 |      React UI        |
                 | Chat + Sources +     |
                 | Artifact Viewer      |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |      FastAPI API     |
                 +----------+-----------+
                            |
                 +----------+-----------+
                 |                      |
                 v                      v
          Session/Message          Agent Layer
             Services                  |
                 |              +-------+-------+
                 |              |               |
                 v              v               v
          PostgreSQL        RAG Retriever    Skills/Tools
          + pgvector             |               |
                 |               v               |
                 |        Transcript Chunks      |
                 |                               |
                 +---------------+---------------+
                                 |
                                 v
                         Provider Abstraction
                           /             \
                          /               \
                       Ollama          Cloud LLM
```

## 3. Backend Boundaries

### API layer

Responsibilities:

- HTTP request validation
- Authentication/session identity boundary as applicable
- Stable response schemas
- HTTP error mapping
- Health endpoints

Should not contain retrieval or provider implementation details.

### Session/message service

Responsibilities:

- Create sessions
- Load session history
- Persist messages
- Enforce session ownership/isolation
- Provide chronological conversation context

### Agent layer

Required implementation:

- Anthropic Claude Agent SDK or Pi Coding Agent
- Thin adapter around the existing application services
- Route user intent to retrieval/answering, writing skill, or artifact generation

The agent should not duplicate the vector database or provider logic.

### RAG layer

Current modules include responsibilities for:

- Loading transcript data
- Normalizing content
- Chunking
- Embedding
- Ingestion
- Retrieval
- Grounded answer construction

This layer is deliberately kept independent of HTTP concerns.

### Provider layer

The provider abstraction standardizes model calls.

Current local provider:

```text
ChatProvider
    |
    +-- OllamaChatProvider
```

Current local chat model:

```text
phi3:latest
```

Current embedding model:

```text
nomic-embed-text
```

Embeddings remain standardized at 768 dimensions so chat-provider changes do not alter the vector schema.

## 4. Knowledge Base

### Ingestion

```text
data/transcripts/*
        |
        v
loader
        |
        v
normalizer
        |
        v
chunker
        |
        v
embedding model
        |
        v
documents + document_chunks
        |
        v
PostgreSQL / pgvector
```

### Idempotency

Documents use source/content identity to prevent unnecessary duplicate ingestion. Chunks are associated with a document and deterministic chunk index.

### Retrieval

```text
User query
   |
   v
Query embedding
   |
   v
pgvector cosine similarity
   |
   v
top-k candidates
   |
   v
relevance threshold
   |
   v
traceable sources
```

## 5. Grounded Answering

The answerer converts retrieved chunks into explicitly identified evidence:

```text
[S1] Transcript source + chunk
[S2] Transcript source + chunk
...
```

The model is instructed to answer only from this context.

If retrieval returns no evidence, the answerer returns a deterministic insufficient-context response and does not invoke the LLM.

Generated citations are sanitized so the response cannot claim a source ID that was not supplied.

## 6. Database Schema

Core entities:

```text
users
  |
  +---- chat_sessions
            |
            +---- messages

documents
  |
  +---- document_chunks
              |
              +---- embedding (pgvector)
```

Important constraints:

- UUID primary keys
- Foreign keys with cascade deletion where appropriate
- Unique document source URL
- Unique `(document_id, chunk_index)`
- Message role validation
- JSONB metadata for extensible source/session metadata

## 7. API Direction

Planned/current vertical slice:

```http
GET  /health

POST /api/sessions
GET  /api/sessions
GET  /api/sessions/{session_id}
DELETE /api/sessions/{session_id}

POST /api/sessions/{session_id}/messages
```

The final API should return structured errors and validation responses.

## 8. Agent Routing

Conceptually:

```text
User request
     |
     v
Agent
     |
     +-- grounded Q&A --> Retriever --> Answerer
     |
     +-- Ship 30 request --> Retrieval --> Ship30 Skill
     |
     +-- artifact request --> Conversation context --> Artifact tool
```

The exact routing mechanism depends on the selected required agent framework, but the application services remain independently testable.

## 9. Provider Selection

Configuration should select the active provider/model without code changes.

```text
LLM_PROVIDER=ollama
LLM_MODEL=phi3:latest
```

A cloud provider can be selected through configuration once its adapter is implemented.

Embedding configuration is intentionally separate:

```text
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
```

This avoids coupling vector dimensions to the chat model.

## 10. Security

### Secrets

- `.env` is local-only.
- `.env.example` contains placeholders/safe defaults.
- API keys must never reach the browser.

### Logs

Do not log:

- raw user prompts
- transcript contents
- complete model answers
- provider credentials

Safe logs may include:

- provider
- model
- retrieval count
- request duration
- failure category
- invalid citation count

### Session isolation

Every message lookup and mutation must be scoped to the requested session and, when user identity exists, the current user.

### Artifact isolation

Generated HTML is untrusted.

Preferred design:

- sanitize allowed markup/styles;
- render inside a sandboxed iframe;
- avoid giving artifact content access to the parent application's DOM, cookies, local storage, or privileged APIs;
- block scripts unless there is a separately reviewed need.

The final implementation should document exactly which tags, attributes, styles, and capabilities are allowed.

## 11. Resilience

Expected failure handling:

```text
DB unavailable
   -> controlled service error

Ollama unavailable
   -> provider unavailable response

Model timeout
   -> bounded timeout + controlled error

No retrieval results
   -> deterministic insufficient-context response

Invalid citations
   -> citation sanitization

Missing environment variable
   -> startup/configuration error with actionable message
```

## 12. Observability

Structured logs should capture operational metadata without sensitive payloads.

Recommended fields:

```text
timestamp
request_id
session_id
operation
provider
model
retrieval_count
duration_ms
status
error_type
```

## 13. Deployment Topology

Target reproducible local deployment:

```text
docker compose
    |
    +-- frontend
    +-- backend
    +-- postgres + pgvector
    +-- optional Ollama host/service strategy
```

The final Docker strategy must account for Ollama being commonly installed on the host machine during the local demo.

## 14. Architectural Trade-offs

### PostgreSQL + pgvector

Chosen over introducing a separate vector database because the assessment already requires PostgreSQL persistence and the knowledge base can remain in the same operational boundary.

### Separate embedding and chat providers

This makes retrieval stable while allowing chat-model experimentation.

### Retrieval-first grounding

Chosen over unrestricted long-context generation because the evaluator needs traceability and reliable unsupported-question behavior.

### Thin agent layer

The agent should orchestrate application capabilities rather than replace deterministic services with opaque prompt logic.

### Local-first demo

Ollama provides a reproducible, credential-free local demonstration while preserving a path to cloud models.
