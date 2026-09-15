# Manual UI Test Plan

## Environment

```bash
docker compose up -d --build
docker compose exec backend python -m app.rag.ingest
```

Open:

```text
http://localhost:5173
```

## 1. Startup

**Steps**

1. Start Docker Compose.
2. Open the frontend.
3. Check the provider badge.

**Expected**

- frontend loads;
- Ollama appears as active;
- no startup exception is visible.

## 2. Grounded question

Ask:

> What are the important signals of product-market fit?

**Expected**

- answer is generated;
- answer contains `[S1]`/`[S2]`-style citations;
- source cards appear;
- source URL is available;
- provider/model is shown.

## 3. Unsupported question

Ask:

> What is Lenny's favorite programming language?

**Expected**

The assistant says it cannot find enough relevant information and does not invent an answer.

## 4. New session isolation

1. Ask a question in Session A.
2. Click New conversation.
3. Ask an unrelated follow-up that depends on Session A.

**Expected**

Session B does not inherit Session A's message history.

## 5. Source traceability

Click a source card's source link.

**Expected**

The source opens in a new browser context and corresponds to the source metadata stored in the document.

## 6. Ship 30

1. Start with a grounded growth question.
2. Click Create Ship 30.
3. Wait for generation.

**Expected**

- artifact workspace shows generation progress;
- final content appears beside chat;
- essay is approximately 1,250 words;
- headings and bullets are present;
- source markers are preserved;
- no unsupported source IDs appear.

For local `phi3`, allow the bounded long-form timeout.

## 7. Artifact viewer

If an HTML artifact path is enabled:

1. Generate an HTML/CSS artifact.
2. Inspect the viewer.

**Expected**

- artifact is rendered beside chat;
- generated HTML is not injected into the main React DOM;
- scripts and inline event handlers are blocked/sanitized;
- artifact cannot access the parent application's storage or DOM.

## 8. Provider failure

Select Anthropic without configuring an API key.

**Expected**

- controlled provider error;
- no secret or traceback in the UI;
- backend remains healthy.

Switch back to Ollama and retry.

## 9. Ollama unavailable

Stop Ollama temporarily.

**Expected**

- model request fails with a controlled error;
- backend process remains running;
- `/api/health` remains reachable if the database/API process is healthy.

Restart Ollama and retry.

## 10. Database failure

Stop the database container.

**Expected**

- affected requests return controlled persistence/database errors;
- API does not expose connection strings;
- restarting the database restores normal operation.

## 11. Re-ingestion

Run ingestion twice:

```bash
docker compose exec backend python -m app.rag.ingest
docker compose exec backend python -m app.rag.ingest
```

**Expected**

The second run reports unchanged documents as skipped and does not create duplicate chunks.

## 12. Final automated check

```bash
cd backend
pytest -q
```

Expected development checkpoint:

```text
97 passed
```
