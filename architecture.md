# Architecture Specification: The Lenny Growth Assistant

---

## 1. System Architecture Overview

The Lenny Growth Assistant is designed according to clean architecture and Forward Deployed Engineering principles: strict separation of concerns, explicit interfaces, defense-in-depth security, and graceful degradation.

### Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                                 USER BROWSER                                    |
|                                                                                 |
|  +-------------------------------------+  +----------------------------------+  |
|  |       React + TypeScript UI         |  |      Isolated Artifact Viewer    |  |
|  |  (Chat Stream, Source Citations,    |  |  (Sandboxed <iframe> without     |  |
|  |   Model Switcher, Session Sidebar)  |  |   scripts, Markdown Viewer)      |  |
|  +------------------+------------------+  +-----------------+----------------+  |
+---------------------|---------------------------------------|-------------------+
                      | HTTP / JSON REST API                  |
                      v                                       v
+---------------------------------------------------------------------------------+
|                             FASTAPI BACKEND                                     |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  |                         API & Middleware Layer                            |  |
|  |  - CORS Middleware      - Structured JSON Logging   - Request ID Tracing  |  |
|  |  - /health (Diagnostics) - /sessions & /messages    - /artifacts          |  |
|  +-------------------------------------+-------------------------------------+  |
|                                        |                                        |
|  +-------------------------------------v-------------------------------------+  |
|  |                     Agent & Routing Orchestrator                          |  |
|  |                                                                           |  |
|  |          +----------------------------------------------------+           |  |
|  |          |                  Intent Classifier                 |           |  |
|  |          +---------+------------------+------------------+----+           |  |
|  |                    |                  |                  |                |  |
|  |          +---------v-------+  +-------v--------+  +------v--------+       |  |
|  |          | Grounded QA     |  | Ship 30 Skill  |  | Artifact      |       |  |
|  |          | Skill           |  | (1250w Essay)  |  | Generator     |       |  |
|  |          +---------+-------+  +-------+--------+  +------+--------+       |  |
|  |                    +------------------+                  |                |  |
|  +---------------------------------------|------------------|----------------+  |
|                                          |                  |                   |
|  +---------------------------------------v-------+  +-------v----------------+  |
|  |                   RAG Engine                  |  |    Security Layer      |  |
|  |  - Query Embeddings (Local/SentenceTransformer) |  | - HTML Tag Sanitizer  |  |
|  |  - pgvector Cosine Search (<=> operator)     |  | - XSS Attack Strip    |  |
|  |  - Metadata Filter & Top-K Ranking           |  | - Sandboxed iframe gen |  |
|  +---------------------------------------+-------+  +------------------------+  |
|                                          |                                      |
|  +---------------------------------------v-----------------------------------+  |
|  |                       LLM Provider Abstraction Layer                     |  |
|  |  +-------------------------------+     +-------------------------------+  |  |
|  |  |    Ollama Provider (Local)    |     |   Anthropic Provider (Cloud)  |  |  |
|  |  |  (phi3-local / llama3 via HTTP)|     |    (Claude 3.5 Sonnet SDK)    |  |  |
|  |  +-------------------------------+     +-------------------------------+  |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------+
|                                PERSISTENCE LAYER                                |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  |                  PostgreSQL 16 with pgvector Extension                    |  |
|  |  - sessions           - messages         - transcripts                    |  |
|  |  - transcript_chunks (vector 384 dim)    - artifacts                      |  |
|  |  (Automatic fallback to SQLite Vector Store for zero-config local run)    |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
```

---

## 2. Database Schema

The database relies on 5 core normalized tables with foreign keys and cascade deletions to prevent session data leakage:

### `sessions`
- `id`: UUID (Primary Key)
- `title`: String (Session title derived from initial prompt)
- `user_id`: String (Nullable, for future user scoping)
- `created_at`: Timestamp (UTC)
- `updated_at`: Timestamp (UTC)

### `messages`
- `id`: UUID (Primary Key)
- `session_id`: UUID (Foreign Key `sessions.id` ON DELETE CASCADE, Indexed)
- `role`: Enum (`user`, `assistant`, `system`)
- `content`: Text (Full message content)
- `intent`: String (Nullable: `grounded_qa`, `ship30`, `artifact_generation`)
- `citations`: JSONB/Text (List of chunk IDs, episode titles, guest, source URLs)
- `created_at`: Timestamp (UTC)

### `transcripts`
- `id`: String (Unique slug e.g. `shreyas-doshi-high-agency-pm`)
- `title`: String (Episode title)
- `guest`: String (Guest name)
- `source_url`: String (YouTube or podcast URL)
- `published_at`: String (Publication date if available)
- `content`: Text (Raw cleaned transcript)
- `created_at`: Timestamp (UTC)

### `transcript_chunks`
- `id`: UUID (Primary Key)
- `transcript_id`: String (Foreign Key `transcripts.id` ON DELETE CASCADE, Indexed)
- `chunk_index`: Integer
- `content`: Text (500–800 tokens)
- `embedding`: Vector(384) (pgvector column with cosine index)
- `metadata_json`: JSONB/Text (Speaker names, start/end timestamps, topic keywords)
- `created_at`: Timestamp (UTC)

### `artifacts`
- `id`: UUID (Primary Key)
- `session_id`: UUID (Foreign Key `sessions.id` ON DELETE CASCADE, Indexed)
- `message_id`: UUID (Foreign Key `messages.id` ON DELETE CASCADE, Indexed)
- `type`: Enum (`markdown`, `html`)
- `title`: String (Human-readable artifact title)
- `content`: Text (Sanitized content)
- `raw_content`: Text (Raw generated content)
- `created_at`: Timestamp (UTC)

---

## 3. Ingestion Pipeline & Chunking

1. **Source Discovery**: Reads all structured JSON/Markdown transcripts in `data/transcripts/`.
2. **Text Cleaning**: Removes noise, audio cues, sponsor interruptions, and normalizes punctuation.
3. **Chunking Strategy**: 
   - Window size: ~500 to 750 tokens (~2,000–3,000 characters).
   - Overlap: 100 tokens (~400 characters) to preserve contextual bridges across speaker turns.
4. **Traceability**: Every chunk retains `transcript_id`, `chunk_index`, `guest`, `title`, and `source_url`. Anonymous vector embeddings are strictly prohibited.
5. **Embedding Generation**: Local embedding pipeline (384-dimensional dense vectors).
6. **Idempotent Upsert**: Chunks are keyed by deterministic UUIDs computed from `(transcript_id, chunk_index)`. Re-running `python scripts/ingest.py` updates existing chunks without duplicating records.

---

## 4. Semantic Retrieval & Grounded RAG

1. **Embedding**: Incoming user query is embedded into a 384-dimensional vector.
2. **pgvector Query**:
   ```sql
   SELECT id, transcript_id, content, metadata_json,
          1 - (embedding <=> :query_vector) AS similarity
   FROM transcript_chunks
   ORDER BY embedding <=> :query_vector ASC
   LIMIT :top_k;
   ```
3. **Relevance Threshold**: Chunks with cosine similarity below threshold (e.g. $< 0.35$) are discarded.
4. **Insufficient Context Refusal**: If zero chunks meet the threshold, the system returns an explicit notice:
   *"The available Lenny's Podcast transcripts do not contain sufficient evidence to answer this question. Please ask about topics covered by guests such as Shreyas Doshi, Elena Verna, Brian Chesky, Gustaf Alströmer, or Casey Winters."*
5. **Prompt Injection Defense**: Transcript context is wrapped in explicit boundaries (`<transcript_context>`) with strict instructions forbidding ungrounded claims.

---

## 5. Agent Layer & Skills

### Intent Router
Classifies incoming requests via deterministic regex heuristics, specialized intent matchers, and LLM zero-shot classification:
- **`ship30`**: Matches keywords like *"Ship 30"*, *"atomic essay"*, *"1250 words"*, *"write an article"*, *"publish a post"*.
- **`markdown_artifact`**: Matches explicit Markdown generation requests (*"create a markdown product strategy"*, *"generate markdown document"*, *"create a spec"*, *"write a document"*). Returns an `ArtifactIntent("markdown_artifact")`.
- **`html_artifact`**: Matches visual web/component requests (*"create a landing page"*, *"generate html/css"*, *"build an html component"*, *"create a dashboard"*). Returns an `ArtifactIntent("html_artifact")`.
- **`artifact_generation`**: Aliased via `ArtifactIntent` class to ensure backward compatibility with legacy tests and callers.
- **`grounded_qa`**: Default route for product, growth, and tactical questions.

### GroundedQASkill
- Formulates answers strictly grounded in retrieved podcast transcript evidence.
- Extracts and returns verified citations with guest name, episode title, and source URL.
- Triggers explicit Insufficient Evidence refusals when query similarity is below the relevance threshold.

### Ship30Skill
Encodes Dickie Bush & Nicolas Cole's Ship 30 for 30 methodology:
- **Headline & Hook**: Clear promise, curiosity gap, specific audience address.
- **Lead-In**: Stakes and context using 1-3-1 cadence.
- **Core Pillars**: Headings, bullet points, selective bold formatting for effortless skimming.
- **Actionable Takeaway**: Concrete next step for immediate execution.
- **Target Length**: ~1,250 words.
- **Citations**: Grounds all claims in the retrieved transcript context.

### ArtifactGeneratorSkill
The Artifact Generator turns conversations and grounded transcript context into persistent deliverables:
1. **Context Ingestion**: Retrieves the last 6 messages from the session dialogue to understand user goals, synthesized takeaways, and domain focus.
2. **Semantic Retrieval**: Queries the vector store using the conversation summary to supply relevant podcast transcript chunks as grounding citations.
3. **Prompt Engineering & Modality Dispatch**:
   - **Markdown Strategy Documents (`markdown`)**:
     - Produces structured documentation with Executive Summary, Strategic Framework, Tactical Pillars, Grounded Evidence Matrix, and Direct Citations.
   - **HTML/CSS Visual Artifacts (`html`)**:
     - Produces self-contained, responsive single-file layouts with an embedded `<style>` block.
     - Follows a dark-slate theme (`#0B0F19`, `#111827`, `#1F2937`, `#6366F1`, `#F9FAFB`).
     - Strictly forbids external scripts, fonts, stylesheets, or inline JS event handlers.
4. **Resilient Generation & Fallback**:
   - Limits token length (`max_tokens=1600`) to guarantee high-speed generation across local Ollama models.
   - Includes deterministic fallback generation if local LLMs time out or fail, ensuring zero downtime.
5. **Persistence & Linkage**:
   - Saves artifact records (`id`, `session_id`, `message_id`, `type`, `title`, `content`, `raw_content`).
   - Links grounding transcript citations from the generating message so the Artifact Viewer can display authoritative sources.

---

## 6. Security Architecture & Sandboxed Isolation

Artifact generation introduces potential untrusted content into the browser environment. The system employs a rigorous **Defense-in-Depth** model:

```
[ LLM Generation / User Input ]
             │
             ▼
   [ Layer 1: Server-Side Sanitizer ]  ──> app.security.sanitizer.sanitize_html()
             │                             - Strips <script>, <iframe>, <object>, <embed>, <form>
             │                             - Removes inline handlers (onerror, onclick, onload...)
             │                             - Nullifies javascript: / vbscript: pseudo-protocols
             ▼
   [ Layer 2: Chat Bubble Isolation ] ──> frontend MessageBubble
             │                             - Zero dangerouslySetInnerHTML in chat bubbles
             │                             - Safe text & token parser for bold, code, citations
             ▼
   [ Layer 3: Viewer Sandboxed Iframe]──> frontend ArtifactViewer
                                           - Rendered in <iframe sandbox="" srcDoc={...}>
                                           - Empty sandbox: NO scripts, NO storage, NO parent DOM
```

### Threat Model & Countermeasures

| Threat Vector | Mechanism | Prevention Layer | Action Taken |
| :--- | :--- | :--- | :--- |
| **XSS via `<script>` Tags** | Direct injection of `<script>alert('xss')</script>` | Server-side sanitizer + Iframe Sandbox | Stripped by BeautifulSoup parser; blocked by `sandbox=""` if any fragment bypasses. |
| **Inline Event Handlers** | Attributes like `<img src=x onerror=alert(1)>` or `<div onclick=...>` | Server-side regex & attribute parser | All `on*` attributes stripped from all HTML tags before storage and delivery. |
| **Pseudo-protocol Links** | `<a href="javascript:alert(1)">` or `<iframe src="javascript:...">` | Server-side URL sanitizer | `javascript:` and `vbscript:` schemes replaced with `about:blank`. |
| **DOM / Cookie Exfiltration** | Script trying to access `window.parent`, `localStorage`, or `document.cookie` | Browser Sandbox Isolation | Empty `sandbox=""` forces iframe into an isolated `null` origin, completely blocking parent DOM/storage access. |
| **Chat Injection via Markdown**| Malicious HTML embedded in assistant chat responses | Frontend chat bubble renderer | Replaced all `dangerouslySetInnerHTML` in chat with a safe React token parser. |

### Sandboxed Iframe Rationale (`sandbox=""`)
In the Artifact Viewer, HTML artifacts are rendered using:
```html
<iframe
  srcDoc={sanitizedContent}
  sandbox=""
  title={artifact.title}
  className="artifact-iframe"
/>
```
By explicitly omitting `allow-scripts` and `allow-same-origin`:
1. **Execution Disablement**: The browser's V8/SpiderMonkey engine disables JavaScript execution inside the iframe document.
2. **Origin Partitioning**: The document inside the iframe is assigned a unique, opaque origin (`null`). Even if a script somehow executed, it cannot access session cookies, tokens, `localStorage`, or the parent DOM tree.
3. **No Top-Level Navigation**: The iframe cannot redirect or alter the location of the host application.

---

## 7. Model Provider Abstraction

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass
```

- **`OllamaProvider`**: Communicates with Ollama REST API (`/api/generate` or `/api/chat`). Default model: `phi3-local` or `llama3`.
- **`AnthropicProvider`**: Communicates with Anthropic Claude API (`claude-3-5-sonnet-20241022`). Enabled seamlessly when `ANTHROPIC_API_KEY` is provided.
- **Dynamic Selection**: Selected via request header `X-LLM-Provider` or JSON payload `provider`.

---

## 8. Observability & Logging

- Structured JSON logs emitted for:
  - `request_received` (Path, method, request ID)
  - `retrieval_started` / `retrieval_completed` (Query, latency ms, chunks matched, top similarity)
  - `retrieval_zero_results` (Warning level)
  - `model_request_started` / `model_request_completed` (Provider, model, token count, duration)
  - `artifact_generated` (Type, length, sanitization flags)
- Secrets and API keys are scrubbed and never logged.
