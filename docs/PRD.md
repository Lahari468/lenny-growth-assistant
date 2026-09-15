# PRD — Lenny Growth Assistant

## 1. Discovery brief

### User

The primary user is a product manager, growth lead, founder, or product-growth practitioner who wants to turn Lenny's material into a decision without manually searching long podcast transcripts.

### Job to be done

> When I have a product or growth question, help me find the relevant Lenny evidence, understand the lesson, and turn it into something I can act on or reuse.

### Pain removed

The assistant removes three pieces of friction:

1. finding relevant transcript material;
2. distinguishing grounded evidence from generic model knowledge;
3. turning an insight into reusable written content.

### Success metrics

**Primary product metric**

- At least 90% of evaluated grounded-answer test cases should cite at least one retrieved source and contain no unsupported factual claim.

**Operational metrics**

- A fresh evaluator can start the stack with one documented Docker Compose command.
- Retrieval and provider failures produce controlled API errors rather than unhandled tracebacks.
- Knowledge-base ingestion is idempotent: rerunning ingestion on unchanged files creates no duplicate chunks.

### Assumptions

- The initial corpus is intentionally small enough for a take-home demo.
- PostgreSQL + pgvector is sufficient; a separate vector database is unnecessary.
- Ollama is the required demo runtime.
- A cloud provider is available as an optional production-quality alternative.
- Transcript redistribution rights must be respected. The repository must not falsely represent synthetic notes as verbatim Lenny transcripts.

## 2. Scope

### Included

- FastAPI API
- PostgreSQL persistence
- pgvector retrieval
- Ollama embeddings and local chat
- Anthropic provider adapter
- Independent conversation sessions
- Source-grounded answers
- Insufficient-context behavior
- Ship 30 writing skill
- Markdown/HTML artifact workflow
- Artifact viewer
- HTML isolation/sanitization strategy
- Docker Compose
- automated tests
- operational documentation

### Intentionally excluded

- Multi-tenant enterprise permissions
- billing
- production cloud deployment
- real-time collaborative editing
- full transcript administration UI
- a separate vector database
- unnecessary microservices

These exclusions keep the take-home focused on the user-visible workflow and reliable handoff.

## 3. Product flows

### Flow A — Start a conversation

1. User opens the application.
2. User clicks New conversation or starts from a suggestion.
3. Frontend creates a session when the first message is submitted.
4. Session ID is persisted.
5. Messages are stored in PostgreSQL.

### Flow B — Ask a grounded question

1. User submits a growth/product question.
2. Query is embedded with the local embedding model.
3. pgvector returns the most relevant chunks.
4. Chunks below the configured similarity threshold are removed.
5. Source metadata is preserved.
6. Grounded prompt is sent to the selected provider.
7. Citations are validated.
8. UI renders the answer and source cards.

### Flow C — Unsupported question

1. User asks something outside the indexed evidence.
2. Retrieval returns no acceptable evidence.
3. Backend returns a controlled insufficient-context response.
4. The assistant does not guess.

### Flow D — Ship 30

1. User asks a growth question or selects Create Ship 30.
2. Backend retrieves evidence.
3. Dedicated Ship30Skill generates the essay.
4. Output is validated for length and source markers.
5. Frontend renders the result in the artifact workspace.

### Flow E — Artifact

1. User requests a Markdown or HTML/CSS artifact.
2. Backend creates structured artifact content.
3. HTML, when enabled, is sanitized/isolated.
4. Artifact appears beside the conversation.
5. User can inspect sources and export Markdown where supported.

## 4. Acceptance criteria

### Grounding

- Relevant questions produce source-backed answers.
- Source IDs match actual retrieved chunks.
- Unsupported questions do not receive fabricated answers.
- Follow-up questions can use session context.

### Sessions

- New conversation creates independent context.
- Session IDs are persistent UUIDs.
- Messages include timestamps.
- Invalid sessions return 404.
- Browser stale-session state is recoverable.

### Models

- Ollama is the demo provider.
- At least one cloud provider is integrated.
- Provider/model choice is visible.
- Missing cloud credentials fail cleanly.
- Ollama timeout is bounded and logged.

### Ship 30

- Dedicated skill exists.
- Target is approximately 1,250 words.
- Hook is explicit.
- Narrative progresses through a central lesson.
- Formatting is skimmable.
- Takeaway is actionable.
- Claims remain grounded.
- Unsupported citation IDs are rejected.

### Artifacts

- Markdown can be generated.
- HTML/CSS can be supported by the artifact path.
- Viewer is beside chat.
- Generated HTML is treated as untrusted.
- Security strategy is documented.

### Operations

- Docker Compose starts the stack.
- `.env.example` contains no secrets.
- Logs identify provider/model/retrieval failures.
- Database and model failures are controlled.
- Ingestion is repeatable and idempotent.

## 5. Risks and trade-offs

| Risk | Decision |
|---|---|
| Hallucination | Retrieval-first prompting + citation validation + refusal behavior |
| Local-model quality | Ollama for required demo; provider abstraction for cloud fallback |
| Long-form latency | Longer bounded timeout only for Ship 30 |
| Retrieval miss | Tunable top-k and similarity threshold |
| Data leakage | Session isolation and safe logs |
| Unsafe HTML | Sanitization + isolated iframe |
| Stale corpus | Idempotent re-ingestion |
| Over-engineering | pgvector inside PostgreSQL instead of a separate vector DB |
| Agent dependency availability | Thin Pi integration with explicit operational fallback |

## 6. Implementation plan

### Completed

- FastAPI backend
- PostgreSQL + pgvector
- ingestion/chunking/embeddings
- retriever
- grounded answer service
- provider abstraction
- persistent sessions
- frontend chat workspace
- source cards
- Ship 30 skill
- artifact workspace
- Docker Compose
- tests and development logs

### Final validation

- fresh Docker startup
- ingestion
- grounded answer
- unsupported-question refusal
- session isolation
- Ship 30 generation
- artifact rendering
- provider failure behavior
- automated tests
- clean Git history
