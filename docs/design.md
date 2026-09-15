# Design — Lenny Growth Assistant

## 1. Design goal

The interface should feel like a focused growth workspace rather than a generic chatbot.

The product should make three things obvious at all times:

1. **what I can ask;**
2. **why I should trust the answer;**
3. **what I can create from the insight.**

## 2. Information architecture

```text
Application
├── Sidebar
│   ├── Brand
│   ├── New conversation
│   ├── Conversation search/list
│   └── Active provider
├── Conversation workspace
│   ├── Header + provider selector
│   ├── Welcome / suggestion state
│   ├── User messages
│   ├── Assistant answers
│   ├── Grounding source cards
│   └── Composer
└── Artifact workspace
    ├── Empty state
    ├── Generation state
    ├── Generated artifact
    └── Source list / export
```

## 3. Visual principles

### Focus

The chat remains the primary surface. Secondary controls are visually quiet.

### Evidence-first trust

Sources appear directly below the answer instead of being hidden in a separate research screen.

### Artifact continuity

Ship 30 generation does not redirect to another page. The artifact workspace stays beside the conversation.

### Restrained visual language

Use a limited neutral palette, strong typography hierarchy, thin borders, and a small number of meaningful status indicators.

### Distinct local-model status

The active provider and model are visible so the evaluator can immediately see that the demo is running on Ollama.

## 4. Key interaction states

### Empty

The welcome state presents:

- a concise product promise;
- example growth questions;
- Create Ship 30 entry point.

### Thinking

The assistant shows a lightweight thinking/loading state while the request is in flight.

### Grounded answer

The answer is followed by:

- source count;
- source cards;
- relevance;
- source title;
- source link.

### Insufficient context

The assistant clearly says the available material does not support the question.

### Artifact generation

The artifact panel communicates progress:

1. retrieve evidence;
2. build narrative;
3. validate citations.

### Artifact success

The artifact replaces the empty state with:

- title;
- rendered content;
- sources;
- export control where applicable.

### Error

Errors should:

- use plain language;
- preserve the conversation;
- offer Retry where safe;
- avoid stack traces and credentials.

## 5. Responsive behavior

Desktop is the primary evaluation layout:

- persistent sidebar;
- conversation center;
- artifact pane.

At narrower widths:

- sidebar collapses;
- artifact workspace can stack below or become a secondary panel;
- composer remains full width;
- source cards wrap without horizontal scrolling.

## 6. Accessibility

- Buttons have descriptive labels.
- Interactive cards have keyboard focus states.
- Color is not the only status signal.
- Form controls expose labels/placeholders.
- Source links use descriptive text.
- Loading and error states are announced through visible status text.
- Generated artifacts remain isolated from the main application DOM.

## 7. Product decisions

### Why sources sit under every answer

Grounding is a core product promise, not a developer-only detail.

### Why provider selection is visible

The assignment explicitly evaluates local Ollama usage and provider flexibility.

### Why Ship 30 is a dedicated skill

The requirement calls for a dedicated writing skill rather than an unstructured one-off prompt. Keeping it in its own service makes its behavior testable and reviewable.

### Why the artifact is beside chat

The user should be able to move from insight to reusable output without losing conversational context.

## 8. Trade-offs

- The design favors desktop clarity over a dense mobile-first layout because the evaluation workflow is desktop-oriented.
- The UI avoids excessive controls to reduce cognitive load.
- Long-form local generation is allowed more time than normal chat because quality and completeness matter more for Ship 30.
