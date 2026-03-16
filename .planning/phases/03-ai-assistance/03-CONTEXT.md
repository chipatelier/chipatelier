# Phase 3: AI Assistance - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add locally-hosted AI assistance to the existing run UI: a log explainer (inline in
LogTerminal), metric-specific explanations (WNS/DRC in PpaMetricCards), a config advisor
(in ConfigEditor), and a multi-turn chat (dedicated AI tab in RunDetail). All inference
runs on local Ollama — design data never leaves the server.

Creating assignments, grading, or layout inspection are separate phases (complete).

</domain>

<decisions>
## Implementation Decisions

### Log Explainer UX
- "Explain Error" button lives inline in the LogTerminal header
- Button is **always visible** regardless of run status (not just on failures) — students can request explanation even for successful stages for learning purposes
- Response renders in a panel **directly below the LogTerminal** (expands on click, collapses when done)
- Response is **cached until a new run is submitted** — no re-firing on tab switch; avoid burning Ollama cycles on repeat views
- Log explainer lives in the **Logs tab only** — not duplicated in Results tab

### Timing and DRC Explain triggers
- "Explain" link/icon appears **next to the WNS metric card** (calls `/explain/timing`) and **next to the DRC count card** (calls `/explain/drc`) in PpaMetricCards
- Response renders in the same below-the-log panel pattern (or a panel below PpaMetricCards)

### Chat UI
- Multi-turn chat lives in a **dedicated AI tab** (5th tab alongside Logs / Results / Layout / VNC)
- AI tab shows a **collapsible context summary** at the top: stage, run status, WNS/DRC metrics, how many log lines were sent — transparent and educational
- Chat history: **last 10 turns** (user+assistant pairs) sent with each request — prevents prompt size from blowing up on small Ollama context windows

### Config Advisor
- "Get AI Suggestions" button in the **ConfigEditor panel** (both form mode and raw mode)
- Advisor is **always available** — can run even before first run (suggestions will be generic without PPA context); when a run exists, suggestions are grounded in actual metrics
- Suggestions displayed as an **advisory list below the button**: per-parameter card showing current value → suggested value + plain-language explanation of why. Student reads and manually adjusts (educational; reasoning visible)

### Streaming & Response Delivery
- **Chat UI: streaming** (token-by-token via SSE or WebSocket) — better perceived latency for conversational back-and-forth
- **Explain and advisor endpoints: wait-for-complete** — simpler implementation, structured output easier to parse; acceptable for one-shot explanations

### Ollama Model
- **Default model: `deepseek-r1:7b`** — strong technical reasoning (timing analysis, RTL concepts), well-suited for ASIC domain
- Model configurable via **`OLLAMA_MODEL` env var** (defaults to `deepseek-r1:7b`); operators can upgrade/downgrade per deployment

### Ollama Unavailability
- When Ollama is unavailable or model not loaded: return **503 with a clear user-visible message** — "AI assistant is currently unavailable. Contact your instructor if this persists."
- No silent failures, no retries, no static hint fallback

### Claude's Discretion
- Exact spinner/loading state design during AI response generation
- Whether explain-below-log panel and explain-below-metrics panel are the same shared component
- Prompt template phrasing (within ASIC/OpenROAD domain context)
- How warm-up is triggered at Ollama service startup (timing, retry logic)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### AI service architecture
- `CLAUDE.md` §"AI Service — Prompt Templates" — context builder injections, what NEVER goes to cloud LLMs
- `CLAUDE.md` §"Environment Variables" — LLM_BACKEND, OLLAMA_BASE_URL, ANTHROPIC_API_KEY env vars

### Existing AI scaffolding (Phase 1)
- `backend/app/ai/llm_client.py` — LLMClient ABC, OllamaClient/AnthropicClient/OpenAIClient stubs, `get_llm_client()`
- `backend/app/ai/context_builder.py` — `build_run_context()` scaffold (log_tail, ppa, config, stage info)
- `backend/app/ai/prompts/__init__.py` — `@register_prompt` decorator pattern, `PROMPT_REGISTRY`
- `backend/app/api/routes/ai.py` — all 5 endpoints scaffolded with 501 stubs; request/response schemas defined

### Frontend integration points
- `frontend/src/components/LogTerminal/LogTerminal.tsx` — where Explain button and response panel attach
- `frontend/src/components/PpaMetricCards/` — where WNS/DRC explain triggers attach
- `frontend/src/components/ConfigEditor/` — where "Get AI Suggestions" button and advisory panel attach
- `frontend/src/pages/RunDetailPage.tsx` — where AI tab is added (5th tab)

### ORFS domain context for prompts
- `CLAUDE.md` §"CTS Stage Details" — CTS timing behavior AI must explain (ideal clock removed after CTS)
- `CLAUDE.md` §"Real ORFS Metrics Schema" — metric key names and what they mean
- `CLAUDE.md` §"Log Streaming Architecture" — log format, stage patterns AI reads

No external ADRs — requirements fully captured in decisions above and CLAUDE.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/ai/llm_client.py`: Full abstract interface scaffolded — Phase 3 fills in `generate()` and `warm_up()` method bodies only; class structure is locked
- `backend/app/ai/context_builder.py`: `build_run_context()` scaffolded — reads Redis `logbuf:{run_id}` and run ORM record; Phase 3 calls this directly
- `backend/app/ai/prompts/__init__.py`: Registry pattern ready — Phase 3 adds prompt template functions using `@register_prompt`
- `backend/app/api/routes/ai.py`: All 5 routes scaffolded with correct request schemas — Phase 3 replaces 501 raises with actual logic
- `frontend/src/hooks/useGradeStream.ts`: Pattern for single-message WebSocket (grade result) — reference for chat streaming implementation

### Established Patterns
- FastAPI dependency injection: `Depends(get_current_user)` already applied to all AI routes
- Zustand store: `jobSlice.ts`, `courseSlice.ts` — add AI state (chat history, explain cache) following same slice pattern
- React tab pattern: `RunDetailPage.tsx` already has multiple tabs — adding AI tab follows existing structure
- Redis log buffer: `logbuf:{run_id}` list already populated by log streamer; `build_run_context()` reads from it

### Integration Points
- `RunDetailPage.tsx` — add "AI ✨" tab; conditionally render `AiAssistantTab` component
- `LogTerminal` component — add "Explain" button in header; render `AiExplainPanel` below terminal
- `PpaMetricCards` — add `[Explain ✨]` link next to WNS and DRC values
- `ConfigEditor` — add "Get AI Suggestions" button; render `AiAdvisorPanel` below editor

</code_context>

<specifics>
## Specific Ideas

- deepseek-r1:7b specifically chosen for ASIC reasoning quality over more generic llama3.x models
- AI tab context summary is intentionally educational — showing students what the AI "knows" helps them understand why they get certain answers
- Advisory list format (current → suggested + plain reasoning) is pedagogically intentional — student learns by reading, not just applying a one-click fix
- Always-visible Explain button (even on successful runs) supports learning mode, not just debugging mode

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-ai-assistance*
*Context gathered: 2026-03-16*
