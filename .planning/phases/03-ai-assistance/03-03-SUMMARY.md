---
phase: 03-ai-assistance
plan: "03"
subsystem: ai
tags: [ollama, streaming, ndjson, react, zustand, typescript, fastapi, pytest]

requires:
  - phase: 03-ai-assistance/03-01
    provides: OllamaClient with chat_stream(), LLM client infrastructure, context_builder
  - phase: 03-ai-assistance/03-02
    provides: explain/advisor endpoints wired, aiSlice base, AiExplainPanel, RunDetailPage tabs

provides:
  - POST /ai/chat endpoint with NDJSON streaming and X-Accel-Buffering: no
  - Think-tag stripping from deepseek-r1 streaming output
  - History cap at 10 turns (20 messages) sent to Ollama
  - streamChat async generator in api/ai.ts for fetch+ReadableStream streaming
  - ChatMessage interface in api/ai.ts
  - aiSlice extended: chatHistory, chatStreaming, appendChatToken, clearChat
  - AiChatTab component with context summary, message list, streaming cursor
  - AI tab as 5th tab in RunDetailPage with tabLabels map

affects:
  - frontend RunDetailPage (AI tab permanently added)
  - backend AI routes (chat no longer 501)

tech-stack:
  added: []
  patterns:
    - NDJSON streaming via FastAPI StreamingResponse with application/x-ndjson media type
    - fetch+ReadableStream async generator pattern for frontend token streaming (no axios buffering)
    - think-tag buffering with in_think state machine to strip <think>...</think> blocks mid-stream
    - Zustand appendChatToken: append-to-last-assistant pattern for incremental token accumulation
    - Tab label map (TAB_LABELS Record<Tab, string>) to decouple display from key names

key-files:
  created:
    - backend/tests/ai/test_chat_routes.py
    - backend/tests/ai/test_chat_streaming.py
    - frontend/src/components/AiChatTab/AiChatTab.tsx
    - frontend/src/components/AiChatTab/index.ts
  modified:
    - backend/app/api/routes/ai.py
    - backend/tests/test_ai_routes.py
    - frontend/src/api/ai.ts
    - frontend/src/store/aiSlice.ts
    - frontend/src/pages/RunDetailPage.tsx

key-decisions:
  - "Chat NDJSON stream: use StreamingResponse with async generator; X-Accel-Buffering: no for nginx pass-through"
  - "Think-tag stripping in backend generate_stream() via in_think state machine — frontend receives only final answer text"
  - "History cap: body.history[-20:] — 10 turns = 20 messages (user+assistant pairs); system not counted"
  - "streamChat as async generator in api/ai.ts (not a hook) — streaming logic co-located with API layer"
  - "appendChatToken accumulates tokens into last assistant message; new assistant entry created if none exists"
  - "TAB_LABELS map in RunDetailPage decouples tab key ('ai') from display label ('AI')"
  - "Streaming cursor uses @keyframes chipCursorBlink injected via <style> tag — no CSS file dependency"
  - "clearChat() called on runId change via useEffect — ensures history never leaks between runs"

patterns-established:
  - "NDJSON streaming endpoint: StreamingResponse + async generator + X-Accel-Buffering no"
  - "Frontend streaming: fetch() + ReadableStream + TextDecoder line-buffering (not axios)"
  - "Zustand token accumulation: appendChatToken checks last message role before push vs append"

requirements-completed:
  - AI-03

duration: 25min
completed: 2026-03-16
---

# Phase 3 Plan 03: Chat Streaming Summary

**NDJSON streaming chat endpoint wired to OllamaClient.chat_stream() with deepseek-r1 think-tag stripping, 10-turn history cap, and AiChatTab React UI with streaming cursor**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-16T23:45:00Z
- **Completed:** 2026-03-16T23:40:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Chat endpoint replaced 501 stub with streaming NDJSON via FastAPI StreamingResponse
- AiChatTab component built with context summary, scrollable message list, streaming cursor (blinking block in #8b5cf6)
- AI tab added to RunDetailPage as 5th tab with proper "AI" label via TAB_LABELS map
- 8 new tests across test_chat_routes.py (5) and test_chat_streaming.py (3) — all 47 AI tests pass
- TypeScript compiles clean

## Task Commits

1. **Task 1: Wire chat streaming endpoint with tests** - `8c5ee05` (feat)
2. **Task 2: Build AiChatTab component and add AI tab** - `8add280` (feat)

## Files Created/Modified

- `backend/app/api/routes/ai.py` - Chat stub replaced with StreamingResponse NDJSON generator
- `backend/tests/ai/test_chat_routes.py` - 5 tests: streaming response, history cap, 404, auth, header
- `backend/tests/ai/test_chat_streaming.py` - 3 tests: token delivery, think-tag stripping, error handling
- `backend/tests/test_ai_routes.py` - Removed test_chat_returns_501 (chat now wired)
- `frontend/src/api/ai.ts` - Added streamChat async generator and ChatMessage interface
- `frontend/src/store/aiSlice.ts` - Extended with chatHistory, chatStreaming, appendChatToken, clearChat
- `frontend/src/components/AiChatTab/AiChatTab.tsx` - Full chat UI with context summary, message list, input bar
- `frontend/src/components/AiChatTab/index.ts` - Re-export
- `frontend/src/pages/RunDetailPage.tsx` - AI tab added; TAB_LABELS map; AiChatTab rendered

## Decisions Made

- Think-tag stripping done in backend via in_think state machine (not frontend) — frontend receives clean text
- streamChat as async generator in api/ai.ts rather than a custom hook — keeps streaming logic in API layer
- TAB_LABELS Record<Tab, string> map decouples tab key from display text for the "ai" vs "AI" case
- Streaming cursor uses @keyframes injected via `<style>` tag (established pattern from StageStatusBar)
- clearChat() on runId change via useEffect — history never leaks between runs

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 3 complete: all three AI features (explain, advisor, chat) are wired
- Chat endpoint ready for integration testing with a live Ollama instance
- AI tab accessible in RunDetailPage for all run states (active and complete)

---
*Phase: 03-ai-assistance*
*Completed: 2026-03-16*

## Self-Check: PASSED

All files exist. Commits 8c5ee05 and 8add280 verified in git log.
