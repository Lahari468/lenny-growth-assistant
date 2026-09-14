Agent Transcript 03 — Grounded Answer Service

Objective

Add reliable answer generation on top of the existing Retriever and ChatProvider without duplicating existing RAG functionality.

Important repository inspection

Before making changes, the existing:

app/rag/answerer.py

was inspected.

The key decision was to reuse the existing implementation where it already satisfied the requirement, rather than generating a second answer pipeline.

Existing implementation behavior

The grounded-answer service:

retrieves relevant chunks;

assigns source identifiers such as [S1] and [S2];

constructs a grounded context block;

calls the configured chat provider;

returns answer text plus source metadata;

sanitizes invalid citation IDs;

logs operational metadata without logging raw prompt, transcript, or answer content.

Critical grounding behavior

If retrieval returns no usable chunks, the service returns a deterministic insufficient-context response.

The LLM is not called in this case.

This was an intentional product decision:

A transparent inability to answer is preferable to an unsupported but fluent answer.

Citation handling

The model is given only the source identifiers supplied by retrieval.

If the model produces a citation that does not correspond to a supplied source, that invalid citation is removed while the real source list is preserved.

This prevents the response from appearing to cite material that was never retrieved.

Tests

Dedicated tests covered:

grounded responses;

empty retrieval;

no-LLM behavior when context is absent;

source mapping;

citation sanitization;

provider errors;

response behavior.

After provider and grounded-answer work, the full test suite reached:

80 passing tests

Engineering judgment

The important decision was not to make the LLM responsible for deciding whether evidence exists. Retrieval establishes the evidence boundary first; generation operates inside that boundary.

Status

Completed and locally verified.
