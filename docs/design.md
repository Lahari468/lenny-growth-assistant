# Design — Lenny Growth Assistant

## 1. Design Objective

The interface should make the assistant feel like a practical internal product tool rather than a developer demo.

The user should be able to:

1. Start or switch conversations.
2. Ask a product/growth question.
3. Understand the answer.
4. Verify the supporting transcript sources.
5. Continue with a follow-up.
6. Generate reusable content.
7. Open generated artifacts beside the conversation.

## 2. Information Architecture

```text
Application
├── Sidebar
│   ├── New Chat
│   └── Session history
│
├── Main Chat
│   ├── User messages
│   ├── Assistant responses
│   ├── Source references
│   └── Composer
│
└── Artifact Viewer
    ├── Artifact title
    ├── Rendered content
    └── Close/open controls
```

## 3. Core Interaction Principles

### Grounding should be visible

Source references should appear close to the claims they support. Users should not need to inspect logs or developer tooling to determine where an answer came from.

### Uncertainty should be explicit

When evidence is insufficient, the interface should clearly communicate that the transcript knowledge base does not support an answer.

### Conversation context should be obvious

The active session should be visually distinct in the sidebar, and starting a new chat should create a clean independent context.

### Artifacts are a second workspace

Generated artifacts should appear beside the conversation rather than replacing it or dumping raw HTML into the chat.

## 4. Interaction States

### Empty state

Explain:

- what the assistant can answer;
- that answers are grounded in Lenny's transcripts;
- example product/growth questions.

### Loading state

Use a clear conversational loading indicator. Avoid exposing raw provider/API terminology to the user.

### Answer state

Show:

- readable response
- source references
- optional provider/model information where useful
- follow-up composer

### No-context state

Use a helpful message explaining that the available transcripts do not contain enough evidence.

### Provider failure

Show a concise recovery message such as retrying or switching the configured provider.

### Artifact state

When an artifact is generated:

- open the viewer beside the chat;
- preserve the conversation;
- allow the user to return to chat without losing context.

## 5. Responsive Behavior

### Desktop

Use a two-pane workspace:

```text
+----------------+-----------------------------+
| Sessions       | Chat             | Artifact |
|                |                  | Viewer   |
+----------------+-----------------------------+
```

### Tablet

Prioritize chat and collapse secondary panels when necessary.

### Mobile

Use one primary pane at a time:

- sessions as a drawer;
- artifact viewer as a full-screen secondary view.

## 6. Accessibility

- Keyboard-accessible controls.
- Visible focus states.
- Semantic buttons and headings.
- Sufficient text contrast.
- Form controls with accessible labels.
- Avoid color-only meaning.
- Loading and error states communicated to assistive technologies.
- Artifact viewer must remain keyboard navigable.

## 7. Visual Direction

The visual system should favor:

- high readability;
- restrained decoration;
- clear hierarchy;
- generous spacing;
- consistent component behavior;
- strong distinction between conversation and generated artifacts.

The UI should feel closer to a polished internal knowledge product than an admin dashboard.

## 8. Artifact Viewer Security UX

The viewer should make a clear distinction between:

- rendered artifact;
- raw source/code, if exposed;
- application controls.

Untrusted generated HTML must be isolated/sanitized. The application must never give generated markup unrestricted access to the parent application.

## 9. Model/Provider Visibility

The user should be able to understand which model/provider is active without making infrastructure the focus of the interface.

A compact status/control can show:

```text
Model: Ollama / phi3:latest
```

A configuration surface can later support a cloud provider.

## 10. Design Trade-offs

### Two-pane artifact workflow

Chosen because the requirement explicitly asks for artifacts beside chat. It also preserves conversational context while allowing the user to inspect the generated output.

### Source-first presentation

Chosen to reinforce trust and make the core product differentiator—grounding—visible.

### Minimal configuration UI

The model provider is an implementation concern, but exposing the active provider helps evaluator trust and demonstrates the flexible-provider requirement.
