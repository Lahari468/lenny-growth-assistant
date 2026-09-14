# Day 2 — Agent + Session API

## Status

Planned development record.

## Objective

Implement the required Anthropic Claude Agent SDK or Pi Coding Agent integration and complete the first conversational vertical slice:

```text
HTTP request
  -> session lookup
  -> agent
  -> retrieval/grounded answer
  -> persistence
  -> response
```

## Verification required

The implementation record must include:

- actual agent framework/dependency used;
- adapter files;
- session endpoints;
- chat endpoint;
- session isolation tests;
- grounding tests;
- persistence tests;
- full test-suite result.

## Important constraint

The agent must be a real integration with the required framework, not a normal direct LLM call renamed as an "agent."
