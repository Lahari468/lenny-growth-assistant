# Agent Development Transcripts

This directory records the AI-assisted development process for the Lenny Growth Assistant.

The purpose is to show how coding-agent output was directed, inspected, tested, corrected, and verified. These records intentionally distinguish implementation work that was completed from work that was only planned.

## Transcript set

1. `01-rag-foundation.md` — initial backend/RAG foundation
2. `02-provider-layer.md` — provider abstraction and Ollama chat provider
3. `03-grounded-answer-service.md` — inspection and verification of the existing grounded answer implementation
4. `04-failures-and-corrections.md` — concrete environment and repository issues discovered during verification
5. `05-agent-session-api-next-step.md` — next agent task prepared after the grounded-answer milestone

## Verification principle

AI-generated code was not treated as automatically correct. The workflow was:

```text
Agent instruction
    ↓
Repository inspection
    ↓
Implementation / reuse
    ↓
Automated tests
    ↓
Local environment verification
    ↓
Failure or mismatch
    ↓
Correction
    ↓
Re-run verification
```

Secrets, credentials, and machine-specific sensitive values must not be committed in these records.
