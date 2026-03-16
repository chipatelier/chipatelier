---
phase: 03-ai-assistance
plan: "02"
subsystem: ai-features
tags: [ai, ollama, explain, advisor, frontend, zustand, react]
dependency_graph:
  requires: ["03-01"]
  provides: ["AI-01", "AI-02"]
  affects: ["frontend/LogTerminal", "frontend/PpaMetricCards", "frontend/ConfigEditor", "backend/ai-routes"]
tech_stack:
  added: []
  patterns:
    - "safe_generate helper: httpx.ConnectError/TimeoutException -> HTTP 503"
    - "AiExplainPanel: cache-first with Zustand explainCache (runId:type key)"
    - "AiAdvisorPanel: regex-parsed suggestion cards with raw fallback"
    - "Inline styles throughout AI components (no Tailwind, no CSS modules)"
key_files:
  created:
    - backend/app/api/routes/ai.py (rewritten from stubs)
    - backend/tests/ai/test_explain_routes.py
    - backend/tests/ai/test_advisor_routes.py
    - frontend/src/api/ai.ts
    - frontend/src/store/aiSlice.ts
    - frontend/src/components/AiExplainPanel/AiExplainPanel.tsx
    - frontend/src/components/AiExplainPanel/index.ts
    - frontend/src/components/AiAdvisorPanel/AiAdvisorPanel.tsx
    - frontend/src/components/AiAdvisorPanel/index.ts
  modified:
    - backend/tests/test_ai_routes.py
    - frontend/src/store/index.ts
    - frontend/src/components/LogTerminal/LogTerminal.tsx
    - frontend/src/components/PpaMetricCards/PpaMetricCards.tsx
    - frontend/src/components/ConfigEditor/ConfigEditor.tsx
    - frontend/src/pages/RunDetailPage.tsx
decisions:
  - "safe_generate catches httpx errors and ollama module errors by module name check; other exceptions propagate"
  - "AiExplainPanel fetches on mount (cache miss), not on user click — panel visible immediately after Explain toggle"
  - "AiAdvisorPanel stores result in Zustand by runId — stale result detectable if user navigates away"
  - "LogTerminal terminal area shrinks to 300px fixed height when explain panel open (flex layout)"
  - "PpaMetricCards wrapped in outer div to accommodate below-grid explain panel without breaking grid layout"
metrics:
  duration: "~10 minutes"
  tasks_completed: 2
  files_created: 9
  files_modified: 6
  tests_added: 11
  completed_date: "2026-03-16"
---

# Phase 3 Plan 02: Explain/Advisor Endpoints + AI Panels Summary

Wired the explain (log/timing/drc) and advisor/config endpoints to Ollama via a `safe_generate` helper, then built the `AiExplainPanel`, `AiAdvisorPanel`, and `aiSlice` Zustand store. Integrated trigger buttons into LogTerminal, PpaMetricCards, and ConfigEditor — delivering AI-01 (log explainer) and AI-02 (config advisor).

## Tasks Completed

| Task | Name | Commit | Key Outputs |
|------|------|--------|-------------|
| 1 | Wire explain/advisor backend endpoints | b95cbea | ai.py rewritten, 11 new tests (7 explain + 4 advisor), test_ai_routes.py updated |
| 2 | Build frontend AI panels and integrate | 63d86bc | AiExplainPanel, AiAdvisorPanel, aiSlice, api/ai.ts; LogTerminal + PpaMetricCards + ConfigEditor updated |

## What Was Built

### Backend (Task 1)

**`backend/app/api/routes/ai.py`** — replaced 501 stubs:
- `safe_generate(prompt, max_tokens)` helper: wraps `llm_client.generate`, catches `httpx.ConnectError`, `httpx.TimeoutException`, and ollama module errors → HTTP 503 with user-facing message
- `_get_run(run_id, db)` helper: fetches run from DB, raises 404 if not found
- `explain_log`, `explain_timing`, `explain_drc`: fetch run, build context, call `PROMPT_REGISTRY[key](ctx)`, call `safe_generate`, return `ExplainResponse`
- `advisor_config`: same pattern, returns `AdvisorResponse`
- `chat`: remains 501 stub (Plan 03)

**Tests** (40 tests total passing):
- `test_explain_routes.py`: 7 tests covering 200 responses, 503 on ConnectError/TimeoutException, 404 on missing run, think-tag stripping
- `test_advisor_routes.py`: 4 tests covering 200 with/without PPA, 503, 404
- `test_ai_routes.py`: updated — removed 501 tests for wired endpoints, kept auth (401) and chat (501) tests

### Frontend (Task 2)

**`frontend/src/api/ai.ts`** — typed API client using shared `apiClient` from `api/client.ts`:
- `explainLog(runId, logLines?)`, `explainTiming(runId)`, `explainDrc(runId)`, `advisorConfig(runId)`

**`frontend/src/store/aiSlice.ts`** — Zustand AI slice:
- `explainCache: Record<string, string>` — keyed by `"${runId}:${explainType}"`
- `clearExplainCacheForRun(runId)` — clears all keys starting with `"${runId}:"`
- `advisorResult: AdvisorResult | null` + `advisorRunId: string | null`

**`frontend/src/components/AiExplainPanel/`** — shared explain panel:
- Cache-first: if `explainCache[runId:type]` hit, renders immediately
- Cache miss: fetches on mount (no user click needed after toggle)
- Purple-themed header (`#1e1433` bg, `#8b5cf6` text), collapsible, privacy footer
- 503 → red banner; other errors → red banner with different message

**`frontend/src/components/AiAdvisorPanel/`** — config advisor panel:
- "Get AI Suggestions ◆" button triggers fetch
- Parses response text with `/^(\w+):\s*(.+?)\s*->\s*(.+?)\s*\|\s*Reason:\s*(.+)$/gm`
- Per-parameter cards when parsing succeeds; raw text fallback otherwise
- No-run-context yellow banner when `runId` is null

**Component integrations:**
- `LogTerminal`: 32px header bar with "Explain" toggle; panel below terminal (terminal shrinks to 300px)
- `PpaMetricCards`: "Explain ◆" on WNS and DRC cards; `AiExplainPanel` below grid
- `ConfigEditor`: "Get AI Suggestions ◆" button added to header; `AiAdvisorPanel` below editor
- `RunDetailPage`: passes `runId` to `PpaMetricCards`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All claimed files verified on disk. Both task commits confirmed in git log.
- b95cbea: feat(03-02): wire explain/advisor endpoints to Ollama with 503 handling
- 63d86bc: feat(03-02): build AiExplainPanel, AiAdvisorPanel, aiSlice and integrate into UI
