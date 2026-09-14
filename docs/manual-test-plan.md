# Manual UI Test Plan

## Environment

- PostgreSQL + pgvector running
- Ollama running on port `11434`
- `nomic-embed-text` installed
- `phi3:latest` installed
- Backend running
- Frontend running

## Test 1 — Application startup

1. Start dependencies.
2. Start backend.
3. Start frontend.
4. Open the application.
5. Verify the UI loads without console-breaking errors.

Expected: application loads with an empty/new-chat state.

## Test 2 — Create session

1. Click New Chat.
2. Verify a new session appears.
3. Refresh the page.

Expected: session remains persisted.

## Test 3 — Grounded question

Ask a question clearly related to the loaded transcripts.

Expected:

- answer is generated;
- answer contains relevant source references;
- sources correspond to retrieved transcript material.

## Test 4 — Follow-up context

Ask a follow-up that depends on the previous question.

Expected: assistant understands the conversational context while grounding the new answer in retrieved evidence.

## Test 5 — Session isolation

1. Ask a question in Session A.
2. Create Session B.
3. Ask a question that would expose whether Session A's messages leaked.

Expected: Session B cannot access Session A's conversation history.

## Test 6 — Unsupported question

Ask for information clearly absent from the transcript knowledge base.

Expected: assistant states that the available material does not support the answer instead of fabricating one.

## Test 7 — Ollama visibility

Verify the configured provider/model is visible where the UI exposes model status.

Expected: local Ollama provider/model is identifiable.

## Test 8 — Provider unavailable

Stop or make Ollama unavailable.

Expected: user sees a controlled error/recovery state, not a raw traceback.

## Test 9 — Ship 30 skill

Request a Ship 30-style essay based on a grounded topic.

Verify:

- approximately 1,250 words;
- strong hook;
- narrative progression;
- headings;
- skimmable formatting;
- useful takeaway;
- claims grounded in transcript sources.

## Test 10 — Artifact generation

Request a Markdown or HTML/CSS artifact.

Expected:

- artifact opens in the Artifact Viewer;
- chat remains available;
- rendered result is readable.

## Test 11 — Artifact security

Use an artifact containing potentially unsafe HTML/script content.

Expected: application does not allow generated content to access the parent application's privileged DOM/storage/context.

## Test 12 — Responsive UI

Test desktop, tablet-width, and mobile-width layouts.

Expected: no critical controls become inaccessible and the chat remains usable.

## Test 13 — Accessibility

Keyboard-navigate:

- new chat;
- session list;
- message composer;
- send action;
- artifact viewer controls.

Expected: all important controls are reachable and visibly focused.

## Test 14 — Empty retrieval

Use a query that should produce no relevant chunks.

Expected: deterministic insufficient-context behavior.

## Test 15 — Database failure

Stop PostgreSQL while making a request.

Expected: controlled service error with no sensitive internal traceback exposed.

## Final evaluator smoke test

A fresh evaluator should be able to:

1. Clone repository.
2. Follow README prerequisites.
3. Configure `.env`.
4. Start PostgreSQL/pgvector and Ollama.
5. Run migrations.
6. Start the application.
7. Ask a grounded question.
8. See sources.
9. Ask a follow-up.
10. Generate a content artifact.
11. Verify local Ollama usage.
