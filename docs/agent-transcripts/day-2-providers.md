# Day 2 — Providers and Grounded Answering

## Objective

Add a model-provider abstraction and implement grounded answer generation using local Ollama.

## Work completed

- `ChatProvider` protocol
- `ChatResponse`
- `ProviderError`
- `OllamaChatProvider`
- configurable Ollama base URL
- separate configurable chat model
- finite model timeout
- safe provider error handling
- grounded answer service
- source IDs such as `[S1]`
- insufficient-context behavior
- citation sanitization
- safe structured logging

## Local models

- `nomic-embed-text:latest`
- `phi3:latest`
- `llama3:latest` was also available locally during development

## Verification

Provider and answerer tests were added and the full suite reached 80 passing tests.

## Important correction

The repository's transcript data is located at:

```text
data/transcripts/
```

rather than:

```text
backend/data/transcripts/
```

The final configuration must use a repository-root-safe path so a fresh clone behaves the same way.

## Engineering principle

The LLM should be replaceable without coupling retrieval storage to the chat provider.
