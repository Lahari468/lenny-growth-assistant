# Agent Transcript 04 — Failures, Corrections, and Verification

## Purpose

This record captures concrete issues found while verifying AI-assisted implementation. These are included because the assessment explicitly asks for failed attempts and corrections.

---

## Issue 1 — PostgreSQL role assumption

### Failure

The initial test configuration assumed a PostgreSQL role named:

```text
postgres
```

with a matching password.

The local development environment did not use that role. The available local PostgreSQL role was the developer's local role.

### Diagnosis

The database role list was inspected with:

```bash
psql -d postgres -c "\du"
```

This showed that the expected local role was different from the generated default.

### Correction

The local `.env` configuration was adjusted to use the actual local PostgreSQL setup.

The important rule was to keep the repository's configuration configurable rather than hard-coding a machine-specific database account.

### Result

The backend tests could run against the local database successfully.

---

## Issue 2 — Ollama server already running

### Failure

Starting another Ollama server produced:

```text
bind: address already in use
```

### Diagnosis

Port `11434` was already occupied by the running Ollama service.

### Correction

The existing service was verified through:

```bash
curl http://localhost:11434/api/tags
```

The available models were confirmed instead of launching a duplicate server.

### Result

Ollama was usable for local embedding and chat verification.

---

## Issue 3 — Transcript path mismatch

### Failure

A backend-relative path assumption led to checking:

```text
backend/data/transcripts/
```

but the actual repository data was located at:

```text
data/transcripts/
```

at repository root.

### Diagnosis

The repository was searched for the transcript file. The sample transcript was found under the root-level data directory.

### Correction

The final application must resolve the transcript directory relative to the repository/project configuration rather than assuming it is nested under `backend/`.

### Result

The source of truth for transcript data was identified.

### Follow-up

Fresh-clone verification is required before final submission to ensure the documented ingestion command works from the evaluator's environment.

---

## Issue 4 — Existing implementation versus unnecessary regeneration

### Situation

When moving toward grounded answering, `app/rag/answerer.py` already existed.

### Correction in approach

Instead of asking the coding agent to generate another answer service, the existing file was inspected and evaluated.

It already had the important behaviors:

- Retriever reuse;
- ChatProvider reuse;
- grounded prompt;
- empty-retrieval protection;
- source IDs;
- citation sanitization;
- safe logging.

### Result

The existing implementation was retained and tested rather than duplicated.

This reduced architectural drift and unnecessary code.

---

## Issue 5 — Generated ZIP required inspection

### Situation

A coding-agent generation produced a `grounded-answer-service.zip`.

### Verification

The ZIP was inspected to confirm what was actually present.

The inspection showed the RAG/provider/answerer work was present, but the required Agent SDK/Pi integration, frontend, Ship 30 skill, artifact viewer, Docker workflow, and other final assessment pieces were not yet present.

### Correction

The next development task was explicitly scoped as a complete Agent + session/chat API vertical slice instead of assuming the project was finished.

### Engineering lesson

Generated artifacts must be inspected and tested. A successful coding-agent response or generated ZIP is not equivalent to a verified feature.
