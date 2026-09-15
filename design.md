# UI/UX Design Specification: The Lenny Growth Assistant

---

## 1. Design Principles & Aesthetics

The Lenny Growth Assistant interface is designed to evoke a modern, high-precision developer and operator tool—combining deep dark slate tones, subtle glassmorphic translucent panels, vibrant accent glows (violet & cyan), and modern typography.

- **Primary Font**: `Plus Jakarta Sans` for clean, human, legible body text and headings.
- **Code Font**: `JetBrains Mono` for code blocks, metrics, and JSON payloads.
- **Color Palette**:
  - Background Canvas: Deep Midnight `#0B0F19`
  - Elevated Cards / Panels: Obsidian Slate `#111827` (with border `#1F2937`)
  - Accent Primary: Electric Violet `#6366F1` / Gradient `#4F46E5 -> #7C3AED`
  - Accent Secondary: Cyan Glow `#06B6D4`
  - Text Primary: Pure White `#F9FAFB`
  - Text Secondary: Muted Silver `#9CA3AF`
  - Warning / Insufficient Context: Amber Glow `#F59E0B`
  - Error / Failure: Coral Crimson `#EF4444`

---

## 2. Information Architecture & Layout

The desktop interface uses a clean multi-column workspace:

```
+---------------------------------------------------------------------------------------------+
|  [🚀 The Lenny Growth Assistant]       [Ollama • phi3-local ▼]   [● Online]   [+ New Chat]  |
+---------------------+---------------------------------------+-------------------------------+
| SESSIONS            | CHAT CONVERSATION                     | ARTIFACT VIEWER               |
|                     |                                       |                               |
| * High Agency PM    | [User] How did Shreyas Doshi define   | [Tab: Rendered HTML] [Source] |
| * Elena Verna PLG   | high agency?                          |                               |
| * Founder Mode      |                                       | +---------------------------+ |
| * Retention Loops   | [Assistant]                           | |  +---------------------+  | |
|                     | Shreyas Doshi defines high agency as  | |  | High Agency PM Matrix |  | |
|                     | the ability to find a way to make     | |  | [Interactive Table]   |  | |
|                     | things happen regardless of the       | |  +---------------------+  | |
|                     | circumstances...                      | +---------------------------+ |
|                     |                                       |                               |
|                     | [Citations: 2 sources]                | Type: HTML • Sandboxed        |
|                     | ┌───────────────────────────────────┐ | Security: No Script Exec      |
|                     | │ Ep 42: Shreyas Doshi • [View Clip]│ |                               |
|                     | └───────────────────────────────────┘ | [Download] [Open Fullscreen]  |
|                     |                                       |                               |
|                     | [ Ask a growth question or Ship 30... ] [ Send ➔ ]                     |
+---------------------+---------------------------------------+-------------------------------+
```

---

## 3. Component Details

### 3.1 Header
- **Logo & Title**: "The Lenny Growth Assistant" with product badge.
- **Model Selector Dropdown**: Clearly indicates active LLM (`Ollama • phi3-local` or `Anthropic • claude-3-5-sonnet`) with status pill indicating backend connectivity.
- **New Chat Action**: Prominent button resetting active session and clearing artifact panel.

### 3.2 Chat Stream & Source Cards
- **User Messages**: Sleek dark bubbles aligned to the right.
- **Assistant Messages**: Formatted markdown rendering headers, lists, code blocks, and bold emphasis.
- **Source Citation Badges**: Expandable accordion cards beneath assistant answers showing:
  - Episode title and guest name.
  - Matched similarity score.
  - Direct clickable source URL (YouTube / Podcast transcript).
  - Exact quoted transcript excerpt.
- **Refusal / Insufficient Context State**: Distinct amber-accented notice clearly stating why evidence was insufficient and suggesting verified guest topics.

### 3.3 Artifact Viewer
The Artifact Viewer resides in a dedicated right-hand split pane, mirroring the Claude Artifacts interaction model:
- **Top Header Bar**:
  - **Artifact Icon & Title**: Displays the document title alongside an icon indicator (`📄` for Markdown, `🌐` for HTML).
  - **Type Pill**: `Markdown Document` or `HTML / CSS Component` with dark-slate badge styling.
  - **Security Indicator**: `Sandboxed (sandbox="")` pill reassuring the user of browser-level script and storage isolation.
  - **View Mode Switcher**: Seamless toggle between `Preview` (visual render) and `Code` (raw source).
  - **Action Buttons**:
    - `Copy`: Copies formatted Markdown or HTML code to system clipboard with visual checkmark confirmation (`Copied!`).
    - `Download`: Generates an instant local `.md` or `.html` file download with safe filename formatting.
    - `Close (✕)`: Dismisses the viewer pane, returning the chat container to centered single-column layout.
- **Main Viewport**:
  - **Markdown Rendering**: Formatted with custom dark-mode CSS—styled `h1`-`h4`, callout blockquotes, tabular data with alternating row highlights, and monospace code blocks.
  - **HTML Visual Render**: Loaded inside `<iframe sandbox="" srcDoc={...}>` ensuring 100% style encapsulation and zero host DOM leakage.
  - **Code View**: Monospace `JetBrains Mono` code presentation with line breaks and scroll containers.
- **Grounding Citations Footer**:
  - Displays transcript source cards that directly grounded the artifact, complete with episode titles, guest names, and deep links.
- **Responsive Layout**:
  - Screens $\ge 1024\text{px}$: Persistent side-by-side view with flexible `50% / 50%` split.
  - Screens $< 1024\text{px}$: Slide-over overlay with backdrop blur and sticky close action.

---

## 4. Interaction States & UX Feedback

| State | Visual Treatment | User Action |
| :--- | :--- | :--- |
| **Empty State** | Centered hero illustration with 3 clickable prompt starter cards ("Elena Verna PLG", "Shreyas Doshi High Agency", "Ship 30 Essay") | Click starter or type query |
| **Loading / Thinking** | Pulsing gradient shimmer with status message: *"Searching transcripts..."* $\rightarrow$ *"Synthesizing grounded answer..."* | Cancelable |
| **Artifact Generating** | Pulsing slate panel in Artifact Viewer with animated shimmer and message: *"Generating artifact from discussion & podcast evidence..."* | Viewer automatically slides open |
| **Artifact Ready** | Seamless transition from skeleton shimmer to rendered view; banner in chat message offering direct "View Artifact" trigger | Preview, copy, download, switch tabs |
| **Zero Results** | Amber alert card stating insufficient evidence with suggested alternative queries | Rephrase query |
| **Ollama Offline** | Warning toast: *"Ollama is unreachable on http://localhost:11434. Run `ollama serve` or switch to Claude."* | Retry button |
| **Artifact Security Failure**| Red alert banner: *"Potentially dangerous script blocked by sanitizer."* with clean sanitized render | View sanitized code |

---

## 5. Accessibility (a11y) & Keyboard Navigation

- Semantic HTML5 landmark tags (`<header>`, `<main>`, `<aside>`, `<section>`, `<article>`).
- Full keyboard operability:
  - `Enter` submits query, `Shift + Enter` inserts newline.
  - `Escape` closes modals and collapses citation cards.
  - `Tab` navigates through inputs, session buttons, and download links.
- High color contrast ratio (exceeding WCAG 2.1 AA standard: $> 4.5:1$ for body text, $> 7:1$ for headings).
