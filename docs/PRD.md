# Product Requirements Document — Lenny Growth Assistant

## 1. Discovery Brief

### User and problem

The primary user is a product or growth practitioner who needs practical guidance from Lenny's Podcast transcripts.

The current problem is not a lack of information; it is the friction of finding, synthesizing, validating, and reusing that information. Long transcript repositories are difficult to query conversationally, and a generic LLM can answer fluently without being grounded in the source material.

The product therefore combines conversational retrieval with explicit source traceability.

### User job

> Ask a product/growth question, receive an answer grounded in Lenny's transcript knowledge base, understand which sources support it, continue the conversation with context, and turn useful answers into reusable content or artifacts.

### Success metrics

Primary product metrics:

- **Grounded answer rate:** percentage of supported questions that include valid transcript source references.
- **Unsupported-answer correctness:** percentage of unsupported questions for which the assistant declines rather than inventing an answer.
- **Task completion:** percentage of test users able to answer a product/growth question and identify the supporting transcript source.
- **Operational reliability:** API requests complete without unhandled errors under normal local-demo conditions.

For the assessment demo, the most important observable success criterion is that an evaluator can ask a question, see a grounded answer, inspect its sources, ask a follow-up, and generate reusable output without understanding the underlying infrastructure.

## 2. Assumptions

1. The transcript repository is the authoritative knowledge source for answers.
2. The initial demo is local and must work with Ollama.
3. PostgreSQL is available locally and pgvector can be enabled.
4. Users are internal/trusted users; full enterprise identity management is outside the assessment scope.
5. Transcript ingestion is primarily batch/refresh-oriented rather than real-time.
6. The evaluator values correctness and traceability more than maximum model creativity.
7. Generated HTML is untrusted and must not execute arbitrary application-accessing code.
8. A cloud model provider is useful for demonstrating model flexibility, while Ollama remains mandatory for the demo.

## 3. Scope

### In scope

- Conversational FastAPI backend
- Independent persisted sessions
- PostgreSQL conversation persistence
- Transcript ingestion and refresh
- Vector retrieval using pgvector
- Grounded answers with source traceability
- Agent layer using the required Anthropic Claude Agent SDK or Pi Coding Agent
- Configurable cloud/local model provider
- Ship 30 for 30 content skill
- Markdown/HTML artifact generation
- In-app artifact viewer
- Safe artifact rendering
- Structured logging and failure handling
- Reproducible local setup
- Automated tests
- Evaluator-oriented documentation

### Intentionally out of scope

- Multi-tenant enterprise authorization
- Fine-tuning a foundation model
- Real-time collaborative editing
- Arbitrary web browsing as an answer source
- Production-scale distributed infrastructure
- Mobile-native applications

These exclusions keep the implementation focused on the assessment's core user journey.

## 4. User Flows

### Flow A — Ask a grounded question

1. User opens the assistant.
2. User starts a new session.
3. User asks a product/growth question.
4. Agent routes the request to retrieval.
5. Relevant transcript chunks are retrieved.
6. Model generates an answer from retrieved evidence.
7. UI displays answer and supporting sources.

### Flow B — Follow-up

1. User asks a follow-up in the same session.
2. Previous messages are loaded from PostgreSQL.
3. Agent receives the relevant conversational context.
4. Retrieval is performed for the follow-up.
5. Answer remains grounded in transcript evidence.

### Flow C — Unsupported question

1. User asks something not supported by the transcript KB.
2. Retrieval produces no sufficiently relevant evidence.
3. Assistant explicitly says the available material does not support the answer.
4. No unsupported factual answer is generated.

### Flow D — Create reusable content

1. User requests a Ship 30-style essay.
2. Agent retrieves relevant evidence.
3. Dedicated writing skill applies the required structure.
4. Output is approximately 1,250 words with hook, narrative progression, skimmable formatting, and useful takeaway.
5. Claims remain grounded in retrieved sources.

### Flow E — Create artifact

1. User requests a Markdown or HTML/CSS artifact.
2. Agent generates the artifact from current conversation context.
3. Backend returns structured artifact content.
4. UI opens an Artifact Viewer beside the conversation.
5. Generated HTML is isolated/sanitized before rendering.

## 5. Acceptance Criteria

### Grounding

- Answers are based on retrieved transcript evidence.
- Sources are visible and traceable.
- Unsupported questions do not receive fabricated answers.

### Sessions

- User can create a new session.
- Each session has an independent conversation history.
- Messages are persisted with timestamps.
- One session cannot read another session's messages.

### Models

- Ollama works for the local demo.
- At least one cloud provider is supported.
- Provider/model configuration can change without changing application code.
- Provider failures return controlled errors.

### Ship 30

- Dedicated skill/tool exists rather than only an inline one-off prompt.
- Output is approximately 1,250 words.
- Strong opening hook.
- Clear narrative progression.
- Headings/bullets/selective emphasis.
- Specific useful takeaway.
- Claims grounded in transcript evidence.

### Artifacts

- Markdown and/or HTML/CSS can be generated.
- Artifact appears beside chat.
- HTML is treated as untrusted.
- Rendering strategy is documented and tested.

### Operations

- Setup is reproducible.
- Environment variables are documented.
- Secrets are not committed.
- Tests cover critical behavior.
- Logs provide enough information to diagnose failures.

## 6. Risks and Trade-offs

| Risk | Mitigation |
|---|---|
| Hallucination | Retrieval-first answering and insufficient-context behavior |
| Weak local model | Keep provider abstraction and allow cloud provider selection |
| Latency | Bounded model timeout and top-k retrieval |
| Cost | Local Ollama for demo; cloud provider is configurable |
| Data leakage | Safe logs, server-side session boundaries, no secrets in frontend |
| Unsafe HTML | Sanitize/isolate generated artifacts |
| Stale transcripts | Idempotent ingestion and refresh workflow |
| Retrieval misses | Tunable top-k/threshold and retrieval tests |
| Agent complexity | Keep agent layer thin and reuse existing RAG/provider services |

## 7. Implementation Plan

### Completed foundation

- Database schema
- Ingestion pipeline
- Embeddings
- Retrieval
- Provider abstraction
- Ollama provider
- Grounded answerer
- Automated tests

### Next

- Agent SDK/Pi integration
- Session/chat API
- Ship 30 skill
- Artifact generation/viewer
- Frontend
- Docker/reproducible startup
- Final cloud provider and deployment validation

## 8. Product Principle

The product should optimize for **trustworthy usefulness**, not simply fluent answers.

A correct refusal with a clear explanation is a successful outcome when the knowledge base does not contain the requested information.
