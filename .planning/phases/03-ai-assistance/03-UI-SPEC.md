---
phase: 3
slug: ai-assistance
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-16
---

# Phase 3 — UI Design Contract

> Visual and interaction contract for AI Assistance frontend components.
> Derived from: 03-CONTEXT.md (locked decisions), 03-RESEARCH.md (patterns), and
> full scan of existing frontend components (Phase 1 + 2 codebase).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | None — plain React inline styles (no Tailwind, no shadcn) |
| Preset | Not applicable |
| Component library | None (no Radix, no base-ui) |
| Icon library | Unicode characters (✓ ✗ ↻) — no icon library installed |
| Font (UI) | `sans-serif` (system stack — no Google Fonts) |
| Font (code/log) | `Menlo, Monaco, 'Courier New', monospace` |
| Styling pattern | Inline `style={{}}` objects on every element; occasional `className` for test targeting |
| Animation | `@keyframes` injected via `<style>` tag in component (see StageStatusBar pattern) |

No shadcn, no Tailwind, no component library. All new Phase 3 components MUST follow the
existing inline-style pattern. Do not introduce new styling dependencies.

---

## Spacing Scale

The codebase uses an informal 4px/8px grid. Derived from existing components:

| Role | Value |
|------|-------|
| xs (inline gap) | 4px |
| sm (element gap) | 8px |
| md (component padding) | 12px |
| lg (section padding) | 16px |
| xl (page padding) | 24px |
| border-radius (small) | 4px |
| border-radius (medium) | 6px |
| border-radius (card) | 8px |
| border-radius (pill/badge) | 12px |

---

## Typography

| Role | Size | Weight | Color token |
|------|------|--------|-------------|
| Page heading (h2) | 18px | 400 | `#f0f6fc` |
| Section heading (h3) | 15px | 400 | `#f0f6fc` |
| Card label / tab label | 12px | 600 | `#8b949e` — uppercase, `letter-spacing: 0.04em` |
| Body / default | 13px | 400 | `#c9d1d9` |
| Secondary / muted | 13px | 400 | `#8b949e` |
| Disabled / ghost | 13px | 400 | `#6e7681` |
| Metric value (large) | 22px | 700 | `#f0f6fc` |
| Score / points label | 18px | 700 | status color |
| Badge / status pill | 11px | 600 | varies — uppercase |
| Code / pre / log | 12–13px | 400 | `#c9d1d9` — monospace |
| AI response prose | 14px | 400 | `#c9d1d9` |

For AI response text: use 14px body size (slightly larger than 13px default) to improve
readability of paragraph-length content. Line-height: 1.6.

---

## Color Tokens

All colors are hardcoded hex. There is no CSS variable system.

### Background Hierarchy

| Token | Value | Usage |
|-------|-------|-------|
| `bg-page` | `#0d1117` | Page / terminal backgrounds |
| `bg-surface` | `#161b22` | Cards, headers, tab bars |
| `bg-elevated` | `#1c2128` | Nested cards, hover states |
| `bg-input` | `#21262d` | Inputs, secondary buttons, copy button |

### Border

| Token | Value | Usage |
|-------|-------|-------|
| `border-default` | `#30363d` | General separators, card outlines |
| `border-subtle` | `#1c2128` | Table row separators |

### Text

| Token | Value | Usage |
|-------|-------|-------|
| `text-primary` | `#f0f6fc` | Headings, active tab, important values |
| `text-secondary` | `#c9d1d9` | Body text, log text |
| `text-muted` | `#8b949e` | Labels, metadata, secondary info |
| `text-ghost` | `#6e7681` | Disabled state, placeholder, empty |

### Semantic (Status)

| Token | Value | Usage |
|-------|-------|-------|
| `green-dot` | `#3fb950` | Success, DRC=0, WNS pass |
| `green-border` | `#1f4022` | Green card border |
| `green-bg` | `#1a3d1a` | Green cell highlight |
| `yellow-dot` | `#d29922` | Warning, partial credit |
| `yellow-border` | `#2d2a1f` | Yellow card border |
| `red-dot` | `#f85149` | Error, violation |
| `red-border` | `#3d1f1f` | Red card border |
| `red-bg` | `#3d1f1f` | Error banner background |
| `blue-action` | `#1f6feb` | Primary buttons, active tab underline |
| `blue-text` | `#58a6ff` | Links, active status |
| `blue-bg` | `#1f3a5f` | Running status badge background |
| `cancel-red` | `#da3633` | Cancel / destructive action button |

### AI-Specific Colors (new in Phase 3)

| Token | Value | Usage |
|-------|-------|-------|
| `ai-accent` | `#8b5cf6` | AI icon tint, AI tab indicator, streaming cursor |
| `ai-accent-bg` | `#1e1433` | AI context summary panel background |
| `ai-accent-border` | `#2d1f4a` | AI context summary panel border |
| `ai-user-bg` | `#1c2128` | User message bubble background |
| `ai-assistant-bg` | `#161b22` | Assistant message bubble background |
| `ai-assistant-border` | `#30363d` | Assistant message bubble border |

Rationale for purple (`#8b5cf6`): All existing semantic colors (green/yellow/red/blue) are
taken by status meanings. Purple is unambiguous as an "AI feature" accent and reads clearly
against the dark `#0d1117` page background.

---

## Component Inventory

### New Components (Phase 3)

---

#### 1. `AiExplainPanel`

**Location:** `frontend/src/components/AiExplainPanel/AiExplainPanel.tsx`

**Purpose:** Shared explain response panel. Used in two places:
- Below the LogTerminal (Logs tab) — triggered by "Explain" button in terminal header
- Below the PpaMetricCards (Results tab) — triggered by "Explain" links on WNS and DRC cards

One component, two mount points. The panel is collapsible and caches its result.

**Props API:**
```typescript
interface AiExplainPanelProps {
  runId: string;
  explainType: "log" | "timing" | "drc";
  // If explainType="log", calls POST /ai/explain/log
  // If explainType="timing", calls POST /ai/explain/timing
  // If explainType="drc", calls POST /ai/explain/drc
}
```

**Visual Spec:**

The panel is a collapsible block that expands below its trigger. Collapsed = 0px height, no
visible content (not rendered at all until first request is made).

Expanded state layout:
```
┌─────────────────────────────────────────────────────────┐
│  ◆ AI Explanation                           [Collapse ▲] │  ← header row: bg #1e1433, border #2d1f4a
│─────────────────────────────────────────────────────────│
│  [loading spinner] Generating explanation...             │  ← loading state (non-streaming)
│  OR                                                       │
│  {prose response text — 14px, line-height 1.6}           │  ← loaded state
│  ─────────────────────────────────────────────────────  │
│  Analyzed by deepseek-r1:7b · Runs locally on this server│  ← privacy footer: 11px, #6e7681
└─────────────────────────────────────────────────────────┘
```

- Header background: `#1e1433`, border: `1px solid #2d1f4a`, border-radius: 6px (top)
- Body background: `#161b22`, padding: 16px
- "◆ AI Explanation" label: 12px, `#8b5cf6`, font-weight 600, uppercase
- Collapse button: 12px, `#6e7681`, float right — text "Collapse ▲" / "Expand ▼"
- Privacy footer: `border-top: 1px solid #30363d`, padding-top: 8px, font-size: 11px, color `#6e7681`
- Max-height: 400px with `overflow-y: auto` on the body (long responses scroll internally)

**Trigger buttons (NOT part of AiExplainPanel — added to parent components):**

In LogTerminal header (add to LogTerminal.tsx):
```
[Explain]   ← 12px, padding 4px 10px, bg #21262d, color #8b5cf6, border 1px solid #2d1f4a, border-radius 4px
```
Position: right side of terminal header bar, alongside "Jump to bottom" area.
The terminal currently has no header bar. Add a thin header bar above the xterm div:
- Height: 32px, background: `#161b22`, border-bottom: `1px solid #30363d`
- Right-aligned: "Explain" button
- The xterm div takes remaining height (flex-grow)

In PpaMetricCards (add to MetricCard for WNS and DRC):
```
[Explain ◆]   ← 11px link-style, color #8b5cf6, no border, cursor pointer, margin-left 8px
```
Rendered inline next to the metric value. Only shown for WNS and DRC cards, not Area/Power.

---

#### 2. `AiAdvisorPanel`

**Location:** `frontend/src/components/AiAdvisorPanel/AiAdvisorPanel.tsx`

**Purpose:** Config parameter suggestion list. Mounted below the ConfigEditor (both form and raw modes).

**Props API:**
```typescript
interface AiAdvisorPanelProps {
  runId: string | null;  // null = no run context (generic suggestions)
  configContent: string; // current config.mk content
}
```

**Visual Spec:**

Trigger button (added to ConfigEditor.tsx header bar):
```
[Get AI Suggestions ◆]
```
- 12px, padding 6px 14px, background `#1e1433`, color `#8b5cf6`, border `1px solid #2d1f4a`,
  border-radius 6px, font-weight 600

Panel below button (collapsed until first request):

Loading state:
```
┌─────────────────────────────────────────┐
│  ◆ Config Advisor                       │
│  [spinner] Analyzing your config...     │
└─────────────────────────────────────────┘
```

Loaded state — per-parameter suggestion cards in a vertical list:
```
┌─────────────────────────────────────────┐
│  ◆ Config Advisor                       │  ← 12px #8b5cf6 label
│─────────────────────────────────────────│
│  ┌──────────────────────────────────┐   │
│  │ CORE_UTILIZATION                 │   │  ← param name: 12px #8b949e uppercase
│  │ 40 → 50                          │   │  ← current → suggested: 15px #f0f6fc bold
│  │ Increasing utilization reduces   │   │  ← explanation: 13px #c9d1d9
│  │ die area without violating your  │   │
│  │ current timing margins (WNS +3.8)│   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │ (next param card)                │   │
│  └──────────────────────────────────┘   │
│─────────────────────────────────────────│
│  Runs locally · No data sent offsite    │  ← privacy footer
└─────────────────────────────────────────┘
```

Per-parameter card:
- Background: `#0d1117`, border: `1px solid #30363d`, border-radius: 6px, padding: 12px 14px
- Param name row: 12px, `#8b949e`, uppercase, font-weight 600, letter-spacing 0.04em
- Current → Suggested row: "40 → 50" — 15px, `#f0f6fc`, font-weight 700; the arrow `→` is `#6e7681`
- Explanation: 13px, `#c9d1d9`, line-height 1.5, margin-top 6px
- No "Apply" button. Advisory only — student adjusts manually. (This is intentional per CONTEXT.md.)

No-run-context disclaimer banner (shown when `runId === null`):
```
┌─────────────────────────────────────────────────────────┐
│  No run metrics available — suggestions are general.    │  ← 12px #d29922, bg #2d2a1f, border #2d2a1f
│  Run your design once for grounded advice.              │
└─────────────────────────────────────────────────────────┘
```

---

#### 3. `AiChatTab`

**Location:** `frontend/src/components/AiChatTab/AiChatTab.tsx`

**Purpose:** Multi-turn chat UI. Mounted as the 5th tab (after Logs / Results / Config / Layout/VNC)
in RunDetailPage. The tab label reads "AI" in the tab bar.

**Props API:**
```typescript
interface AiChatTabProps {
  runId: string;
}
```

**Layout (full-height flex column):**
```
┌────────────────────────────────────────────────────────┐
│  ▾ Context: Stage cts · Status complete · WNS +3.8ns   │  ← collapsible context summary
│    DRC 0 · 50 log lines sent · deepseek-r1:7b          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  [message list — scrollable, flex-grow: 1]             │
│                                                        │
│  You: Why did timing get worse after CTS?              │  ← user message (right-aligned bubble)
│                                                        │
│  AI: After CTS, OpenROAD removes the ideal clock       │  ← AI message (left-aligned)
│  assumption and inserts real clock buffers. This       │
│  reveals true setup/hold violations that were hidden   │
│  during placement...                          [cursor] │  ← streaming cursor: blinking █ #8b5cf6
│                                                        │
├────────────────────────────────────────────────────────┤
│  [text input — "Ask about your run..."]    [Send ▶]    │  ← input bar
└────────────────────────────────────────────────────────┘
```

**Context Summary Panel (collapsible, top of tab):**
- Background: `#1e1433`, border-bottom: `1px solid #2d1f4a`, padding: 10px 16px
- "▾ Context:" label: 12px, `#8b5cf6`, font-weight 600
- Collapsed: single line showing summary. Expanded: multi-line detail.
- Toggle: click anywhere on the summary bar
- Content (all 13px `#8b949e`):
  - Stage: `{stage_completed}` or "not started"
  - Status: `{run status}`
  - WNS: `{worst_negative_slack} ns` or "—"
  - DRC: `{drc_routing_errors}` violations or "—"
  - Log lines sent: `{N} log lines`
  - Model: `deepseek-r1:7b`
- No student name, no email, no file paths in this panel.

**Message List:**
- Scrolls independently (overflow-y: auto, flex-grow: 1)
- Auto-scrolls to bottom as new tokens arrive
- Empty state (no messages): centered text "Ask anything about your run." — 14px `#6e7681`

User message bubble (right-aligned):
- `margin-left: auto`, `max-width: 70%`, `background: #1c2128`, `border: 1px solid #30363d`,
  `border-radius: 12px 12px 2px 12px`, padding: 10px 14px
- Text: 14px `#c9d1d9`, line-height 1.5
- Label above bubble: "You" — 11px `#6e7681`, text-align right, margin-bottom 4px

Assistant message bubble (left-aligned):
- `margin-right: auto`, `max-width: 85%`, `background: #161b22`, `border: 1px solid #30363d`,
  `border-radius: 2px 12px 12px 12px`, padding: 10px 14px
- Text: 14px `#c9d1d9`, line-height 1.6 (slightly more line-height than user for readability)
- Label above bubble: "AI" — 11px `#8b5cf6`, font-weight 600, margin-bottom 4px
- Streaming cursor: append `█` in `#8b5cf6` while `chatStreaming === true` on the last message;
  remove cursor when `done` token arrives

Message list padding: 16px top/bottom, 16px left/right, gap 16px between message groups.

**Input Bar:**
- Background: `#161b22`, border-top: `1px solid #30363d`, padding: 12px 16px
- textarea (not input): 3 rows max, auto-resize; background `#0d1117`, border `1px solid #30363d`,
  border-radius 6px, padding 8px 12px, color `#c9d1d9`, font-size 14px, resize: none
  Placeholder: `"Ask about your run..."`
- Send button: padding 8px 16px, background `#1f6feb`, color `#fff`, border none,
  border-radius 6px, font-size 13px, font-weight 600 — disabled (background `#21262d`,
  color `#6e7681`) while streaming or input is empty
- Keyboard: Enter submits; Shift+Enter inserts newline

---

### Reused Components (Phase 1/2 — unchanged)

| Component | Phase | How Phase 3 uses it |
|-----------|-------|---------------------|
| `LogTerminal` | 1 | Gets "Explain" button added to new header bar |
| `PpaMetricCards` | 1 | Gets "Explain ◆" links on WNS and DRC `MetricCard` instances |
| `ConfigEditor` | 2 | Gets "Get AI Suggestions ◆" button added to header bar |
| `StageStatusBar` | 1 | No change — still renders above tabs |
| `RunDetailPage` | 1 | Adds "AI" as 5th tab; renders `AiChatTab` |

---

## Interaction Contracts

### Tab Addition (RunDetailPage)

The 5 tabs after Phase 3: `Logs | Results | Config | Layout | AI`

The AI tab is:
- Always enabled (never locked/disabled — chat works even during an active run)
- Label in tab bar: `"AI"` — same style as other tabs; active underline `#1f6feb`
- No "(locked)" annotation needed

Add `"ai"` to the `Tab` type in `RunDetailPage.tsx`:
```typescript
type Tab = "logs" | "results" | "config" | "layout" | "ai";
```

### Loading States

**AiExplainPanel — loading (non-streaming, wait-for-complete):**
- Show animated spinner + "Generating explanation..." text while request is in-flight
- Spinner: inline SVG circle (no library) — 16px, stroke `#8b5cf6`, `animation: spin 1s linear infinite`
- No skeleton, no shimmer — simple spinner + text is consistent with codebase style

**AiAdvisorPanel — loading:**
- Same spinner pattern + "Analyzing your config..."

**AiChatTab — streaming:**
- Send button enters disabled state immediately on submit
- Streaming cursor (`█`) appended to last assistant message token-by-token
- No separate loading indicator in the input bar — the cursor IS the progress indicator
- When `done` arrives: cursor removed, send button re-enabled

### Error States

**Ollama 503 (unavailable):**
All three components show the same error banner pattern:
```
┌──────────────────────────────────────────────────────────────────┐
│  AI assistant is currently unavailable.                          │  ← 13px #f85149
│  Contact your instructor if this persists.                       │
└──────────────────────────────────────────────────────────────────┘
```
- Background: `#3d1f1f`, border: `1px solid #da3633`, border-radius: 6px, padding: 10px 14px
- No retry button. No stale content shown. Error replaces loading state entirely.
- "AI assistant loading..." is shown while backend returns 503 during model warm-up
  (same banner — exact text from 03-CONTEXT.md: "AI assistant is currently unavailable.
  Contact your instructor if this persists.")

**Network / HTTP error (non-503):**
- Same banner. Text: "Failed to reach AI service. Check your connection and try again."

**Chat streaming error (mid-stream failure):**
- Append error message after the partial assistant bubble: `[Response interrupted — please try again]`
  — 13px, italic, `#f85149`. Send button re-enabled.

### Empty States

| Location | Empty state |
|----------|-------------|
| AiExplainPanel (not yet triggered) | Panel not rendered at all — invisible until first click |
| AiAdvisorPanel (not yet triggered) | Panel not rendered at all |
| AiChatTab (no messages) | Centered: "Ask anything about your run." 14px `#6e7681` |
| AiAdvisorPanel (no suggestions returned) | "No suggestions at this time. Try running a complete flow first." 13px `#6e7681` |

### Explain Panel Cache Behavior

- `AiExplainPanel` reads from `aiSlice.explainCache[runId + ":" + explainType]`
- On cache hit: show cached response immediately (no spinner, no request)
- Cache key: `${runId}:${explainType}` — scoped to both run and type
- Cache cleared: on new run submission (clear all keys for old runId)
- Collapse/expand is purely local state — does not affect cache

### Collapsible Panels

Both `AiExplainPanel` and the context summary in `AiChatTab` are collapsible.

Collapse toggle behavior:
- Collapsed: content `display: none` (not height 0) — avoids layout jank on long content
- The "Collapse ▲" / "Expand ▼" button toggles a local boolean state
- Default state: expanded when content is present, collapsed when empty

### Chat History Trim (frontend display)

The frontend stores the full chat history in `aiSlice.chatHistory`.
Only the last 10 turns (user+assistant pairs = 20 messages) are sent to the backend per request.
The UI shows all messages in the scroll list — no truncation indicator needed (history is small).
Chat history is cleared when the user navigates to a different run.

---

## Copywriting

### Buttons

| Button | Label |
|--------|-------|
| Log explain trigger | `Explain` |
| WNS explain trigger | `Explain ◆` |
| DRC explain trigger | `Explain ◆` |
| Config advisor trigger | `Get AI Suggestions ◆` |
| Chat send | `Send` |
| Collapse panel | `Collapse ▲` |
| Expand panel | `Expand ▼` |

The `◆` character (U+25C6, Black Diamond) is used as the AI feature marker — consistent,
no icon dependency, legible at 12px.

### Placeholder Text

| Field | Placeholder |
|-------|-------------|
| Chat input | `Ask about your run...` |

### Panel Labels

| Panel | Label |
|-------|-------|
| Explain panel header | `◆ AI Explanation` |
| Advisor panel header | `◆ Config Advisor` |
| Chat tab context bar | `▾ Context:` |

### Status / Feedback Text

| State | Text |
|-------|------|
| Explain loading | `Generating explanation...` |
| Advisor loading | `Analyzing your config...` |
| Chat empty state | `Ask anything about your run.` |
| AI unavailable (503) | `AI assistant is currently unavailable. Contact your instructor if this persists.` |
| AI loading (503 during warmup) | Same as above — no separate "loading" text; 503 is the signal |
| No run context disclaimer | `No run metrics available — suggestions are general. Run your design once for grounded advice.` |
| Advisor no results | `No suggestions at this time. Try running a complete flow first.` |
| Chat stream interrupted | `[Response interrupted — please try again]` |

### Privacy Footer

Used in `AiExplainPanel`, `AiAdvisorPanel`:
```
Analyzed by deepseek-r1:7b · Runs locally on this server
```

Used in `AiChatTab` context summary bar (as a sub-line, not a separate footer):
```
deepseek-r1:7b · runs locally
```

Exact text. Both lines are 11px `#6e7681`. No shield icon, no lock icon — plain text.

---

## Accessibility

### ARIA Labels

| Element | ARIA |
|---------|------|
| AiExplainPanel container | `role="region"`, `aria-label="AI explanation panel"` |
| AiAdvisorPanel container | `role="region"`, `aria-label="AI config advisor panel"` |
| AiChatTab message list | `role="log"`, `aria-live="polite"`, `aria-label="AI chat messages"` |
| Chat input textarea | `aria-label="Chat message"` |
| Send button | `aria-label="Send message"` (disabled: `aria-disabled="true"`) |
| Collapse/expand toggle | `aria-expanded={isExpanded}`, `aria-controls="{panel-id}"` |
| Explain trigger button | `aria-label="Get AI explanation for this log"` / `"...for WNS"` / `"...for DRC"` |
| Context summary bar | `role="note"`, `aria-label="AI context summary"` |
| Loading spinner | `aria-label="Loading AI response"`, `role="status"` |
| Per-param card | `role="article"` |

### Keyboard Navigation

| Interaction | Key |
|-------------|-----|
| Submit chat message | Enter |
| Insert newline in chat input | Shift+Enter |
| Toggle collapse panel | Enter or Space on collapse button |
| Dismiss error banner | Not dismissable — user must retry or leave |

### Screen Reader

- AI response text is rendered as plain text in a `<div>` — no markdown rendering.
  This keeps screen reader output predictable.
- The streaming cursor `█` is inside a `<span aria-hidden="true">` — screen readers
  do not announce individual token arrivals.
- When streaming completes, a visually-hidden `<span aria-live="assertive">` announces
  "AI response complete" once.
- Chat messages: each message is a `<div role="article">` with `aria-label="You said: {text}"`
  or `aria-label="AI response: {text}"`.

---

## Privacy Constraints (Critical)

### What the UI must never display in AI panels

- Student email address or display name
- File system paths (ARTIFACTS_ROOT, container paths)
- GDS or DEF file content
- PDK file names or library paths
- Other students' data

The AI context summary in `AiChatTab` shows only: stage, status, WNS, DRC count, log line count,
model name. It does NOT show: user ID, project ID, full log, config values, file paths.

### Privacy indicator

Every panel that calls an AI endpoint (AiExplainPanel, AiAdvisorPanel, AiChatTab) includes the
privacy footer:
```
Runs locally on this server
```
This text must always be visible when AI content is shown. Its purpose is to assure students
that their design data does not leave the institution's server.

There is no shield icon, no certification badge, no modal explaining privacy in detail. The
plain-text footer is intentional — educational tool, not a compliance document.

### No "Send to cloud" escape hatch in the UI

There is no UI control to switch LLM providers. The `LLM_BACKEND` env var is operator-only.
The frontend always shows the local model name (`deepseek-r1:7b` by default, or the value
returned by the `/ai/status` endpoint if one is added in future phases).

---

## Responsive Behavior

The existing application has no mobile breakpoints. All layouts are fixed-width desktop. Phase 3
follows the same approach — no new responsive behavior introduced.

### AiChatTab at narrow viewport (< 800px wide)

The chat panel naturally fills the tab content area. If the viewport is narrow:
- Message bubbles: `max-width` clamps to 90% of available width (instead of 70%/85%)
- Context summary: truncate at one line (no expand on mobile — not a priority)
- Input bar: full width, send button at right edge

This is a best-effort degradation, not a designed mobile layout.

### AiExplainPanel and AiAdvisorPanel

Both are block-level elements that expand below their parent. They fill the container width
naturally and do not require responsive rules.

---

## Component File Structure

```
frontend/src/
├── api/
│   └── ai.ts                      # NEW: typed API calls (explainLog, explainTiming,
│                                  #      explainDrc, advisorConfig, chatStream)
├── hooks/
│   └── useAiStream.ts             # NEW: fetch+ReadableStream hook for chat token streaming
│                                  #      Pattern: same as useGradeStream.ts
├── store/
│   └── aiSlice.ts                 # NEW: Zustand slice
│                                  #      explainCache: Record<string, string>
│                                  #      advisorResult: AdvisorResult | null
│                                  #      chatHistory: ChatMessage[]
│                                  #      chatStreaming: boolean
└── components/
    ├── AiExplainPanel/
    │   ├── AiExplainPanel.tsx     # NEW: explain response panel (shared)
    │   └── index.ts               # re-export
    ├── AiAdvisorPanel/
    │   ├── AiAdvisorPanel.tsx     # NEW: advisor suggestion list panel
    │   └── index.ts               # re-export
    └── AiChatTab/
        ├── AiChatTab.tsx          # NEW: multi-turn chat UI
        └── index.ts               # re-export
```

Modified files:
- `frontend/src/components/LogTerminal/LogTerminal.tsx` — add header bar + "Explain" button
- `frontend/src/components/PpaMetricCards/PpaMetricCards.tsx` — add "Explain ◆" to WNS and DRC cards
- `frontend/src/components/ConfigEditor/ConfigEditor.tsx` — add "Get AI Suggestions ◆" button
- `frontend/src/pages/RunDetailPage.tsx` — add "AI" tab, render `AiChatTab`
- `frontend/src/store/index.ts` — add aiSlice to store

---

## Implementation Notes for Executor

1. **No new npm dependencies.** All UI is inline styles + existing libraries. The research doc
   confirms no frontend deps needed (`@microsoft/fetch-event-source` explicitly NOT needed).

2. **LogTerminal header bar.** The current `LogTerminal` has no header. Add a 32px flex row above
   the xterm `div`. The total component height stays 100% — the xterm div loses 32px to the header.
   Use `calc(100% - 32px)` or a flex column with `flex: 1` on the xterm div.

3. **AiExplainPanel mounting.** In the Logs tab, the panel mounts below the LogTerminal in the tab
   content div. In the Results tab, the panel mounts below PpaMetricCards. The component itself
   is identical — only the `explainType` prop changes. The `runId` is passed from the page.

4. **Non-streaming explain/advisor.** The `api/ai.ts` functions for explain and advisor use
   standard `axios.post` — not the streaming hook. Only `chatStream` uses `useAiStream`.

5. **Streaming cursor removal.** When the NDJSON stream yields `{"done": true}`, the Zustand
   `chatStreaming` flag is set to false. The streaming cursor span is conditionally rendered
   based on `chatStreaming && isLastMessage`.

6. **`<think>` tag stripping.** This happens in the backend (`OllamaClient.generate()`). The
   frontend does not need to strip anything — all text received is final answer text.

7. **Tab order in RunDetailPage.** The existing tabs are `["logs", "results", "config"]`.
   After Phase 2, a "layout" tab may exist. The AI tab is always the last tab. Add it at the
   end of the tab array regardless of intervening additions.
