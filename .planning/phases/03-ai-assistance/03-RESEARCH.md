# Phase 3: AI Assistance - Research

**Researched:** 2026-03-16
**Domain:** Local LLM inference (Ollama), FastAPI SSE streaming, prompt engineering, React streaming UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Log Explainer UX**
- "Explain Error" button lives inline in the LogTerminal header
- Button is always visible regardless of run status (not just on failures)
- Response renders in a panel directly below the LogTerminal (expands on click, collapses when done)
- Response is cached until a new run is submitted — no re-firing on tab switch
- Log explainer lives in the Logs tab only

**Timing and DRC Explain triggers**
- "Explain" link/icon appears next to the WNS metric card (calls `/explain/timing`) and next to the DRC count card (calls `/explain/drc`) in PpaMetricCards
- Response renders in the same below-the-log panel pattern (or a panel below PpaMetricCards)

**Chat UI**
- Multi-turn chat lives in a dedicated AI tab (5th tab alongside Logs / Results / Layout / VNC)
- AI tab shows a collapsible context summary at the top: stage, run status, WNS/DRC metrics, how many log lines were sent
- Chat history: last 10 turns (user+assistant pairs) sent with each request

**Config Advisor**
- "Get AI Suggestions" button in the ConfigEditor panel (both form mode and raw mode)
- Advisor is always available — can run even before first run
- Suggestions displayed as an advisory list below the button: per-parameter card showing current value → suggested value + plain-language explanation

**Streaming & Response Delivery**
- Chat UI: streaming (token-by-token via SSE or WebSocket)
- Explain and advisor endpoints: wait-for-complete (non-streaming)

**Ollama Model**
- Default model: `deepseek-r1:7b`
- Model configurable via `OLLAMA_MODEL` env var (defaults to `deepseek-r1:7b`)

**Ollama Unavailability**
- When Ollama is unavailable or model not loaded: return 503 with a clear user-visible message
- No silent failures, no retries, no static hint fallback

### Claude's Discretion
- Exact spinner/loading state design during AI response generation
- Whether explain-below-log panel and explain-below-metrics panel are the same shared component
- Prompt template phrasing (within ASIC/OpenROAD domain context)
- How warm-up is triggered at Ollama service startup (timing, retry logic)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AI-01 | User can request a plain-language explanation of ORFS log errors from the last N lines of a failed stage (local Ollama inference — design data stays on-premise) | Ollama `/api/generate` non-streaming call; context_builder log_tail injection; `@register_prompt("explain_log")` pattern |
| AI-02 | User can request config parameter suggestions based on current run's PPA metrics (local Ollama inference) | Ollama non-streaming call; PPA JSONB mapped via METRIC_MAP; advisor prompt template with CURATED_PARAMS list |
| AI-03 | User can chat with an AI assistant that has context of their current run; Ollama model warmed on service startup | Ollama `/api/chat` streaming with SSE; `keep_alive: -1` warm-up at startup via FastAPI lifespan; chat history last-10-turns capped |
</phase_requirements>

---

## Summary

Phase 3 wires three AI features (log explainer, config advisor, multi-turn chat) into the existing scaffolded interface. All five backend route stubs in `backend/app/api/routes/ai.py`, the `OllamaClient`, `build_run_context()`, and `PROMPT_REGISTRY` already exist — Phase 3 fills in the method bodies, adds prompt template functions, and builds the frontend UI components.

The primary integration dependency is the Ollama REST API, which runs as a sidecar service in Docker Compose. The `ollama` Python library (v0.6.1, wraps httpx) is the standard approach for calling Ollama from FastAPI. For the chat streaming endpoint, FastAPI's `StreamingResponse` with an async generator yields newline-delimited JSON chunks to the frontend. The React frontend streams via `fetch()` with `ReadableStream` iteration (not native `EventSource`, because native `EventSource` cannot send `Authorization` headers).

The deepseek-r1:7b model (4.7 GB) outputs reasoning inside `<think>...</think>` tags before the final answer. All AI response processing must strip these tags from non-chat responses (explain/advisor), and optionally expose them in chat. Model warm-up uses a single `POST /api/generate` with `keep_alive: -1` and no prompt — this loads the model into memory and pins it without timeout.

**Primary recommendation:** Use the `ollama` Python package AsyncClient for all backend calls. For chat streaming, use FastAPI `StreamingResponse` yielding JSON fragments. For the frontend streaming hook, use `fetch` with `ReadableStream` (same pattern as `useLogStream` but for SSE-style chunks).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ollama` (Python) | 0.6.1 | Async Ollama client with streaming | Official library; wraps httpx; AsyncClient with `stream=True` for chat |
| `httpx` | 0.27.x | Already in pyproject.toml | Used internally by `ollama` library; available for direct calls if needed |
| FastAPI `StreamingResponse` | (FastAPI 0.115.x) | Stream chat tokens to browser | Built-in; async generator pattern; no new deps |
| Zustand | 5.0.x | Frontend AI state slice | Already used for job/course/auth slices; same pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@microsoft/fetch-event-source` | npm | SSE with auth headers on frontend | NOT NEEDED — prefer raw `fetch` + `ReadableStream` since project already uses raw fetch for WS |
| `sse-starlette` | Python | FastAPI SSE helper | NOT NEEDED — `StreamingResponse` with NDJSON chunks is sufficient and simpler |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ollama` Python lib | Direct `httpx.AsyncClient` | ollama lib is cleaner; direct httpx needed only if you need full control over streaming internals |
| `StreamingResponse` NDJSON | `sse-starlette` EventSourceResponse | SSE adds reconnect/retry semantics; not needed for one-off chat stream; NDJSON simpler |
| `fetch` + ReadableStream | native `EventSource` | EventSource can't set Authorization header; fetch required |

**Installation (backend — new dependency only):**
```bash
uv add ollama==0.6.1
```

No new frontend dependencies required.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/ai/
├── llm_client.py         # EXISTING: fill in OllamaClient.generate() + warm_up()
├── context_builder.py    # EXISTING: build_run_context() ready to use
├── prompts/
│   ├── __init__.py       # EXISTING: PROMPT_REGISTRY + @register_prompt decorator
│   ├── explain.py        # NEW: explain_log, explain_timing, explain_drc templates
│   └── advisor.py        # NEW: advisor_config template
backend/app/api/routes/
└── ai.py                 # EXISTING: replace 501 stubs with Ollama calls

frontend/src/
├── api/
│   └── ai.ts             # NEW: typed API client (explain, advisor, chat streaming)
├── hooks/
│   └── useAiStream.ts    # NEW: fetch+ReadableStream hook for chat token streaming
├── store/
│   └── aiSlice.ts        # NEW: Zustand slice (explain cache, chat history, advisor state)
└── components/
    ├── AiExplainPanel/   # NEW: shared explain response panel (used by LogTerminal + PpaMetricCards)
    ├── AiAdvisorPanel/   # NEW: config advisor list panel (used by ConfigEditor)
    └── AiChatTab/        # NEW: multi-turn chat UI with context summary
```

### Pattern 1: Non-Streaming Ollama Call (Explain + Advisor)

**What:** POST to Ollama `/api/generate` with `stream=False`; await full response; return as JSON.
**When to use:** All explain endpoints and advisor endpoint (one-shot, structured output expected).

```python
# Source: ollama Python library docs + Ollama API reference
from ollama import AsyncClient

class OllamaClient(LLMClient):
    def __init__(self, base_url: str, model: str = "deepseek-r1:7b"):
        self._client = AsyncClient(host=base_url)
        self._model = model

    async def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        response = await self._client.generate(
            model=self._model,
            prompt=prompt,
            options={"num_predict": max_tokens},
            stream=False,
            keep_alive=-1,   # keep model loaded after this call
        )
        raw = response["response"]
        # Strip <think>...</think> reasoning traces from deepseek-r1
        import re
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    async def warm_up(self) -> None:
        # Preload model: send empty generate with keep_alive=-1
        # This pins model in memory indefinitely (until Ollama restart)
        try:
            await self._client.generate(
                model=self._model,
                prompt="",
                keep_alive=-1,
            )
        except Exception:
            # Non-fatal: model loads on first real request
            pass
```

### Pattern 2: Streaming Ollama Call (Chat endpoint)

**What:** POST to Ollama `/api/chat` with `stream=True`; yield chunks via FastAPI `StreamingResponse`.
**When to use:** `/ai/chat` endpoint only.

```python
# Source: ollama Python library AsyncClient streaming + FastAPI StreamingResponse
from fastapi.responses import StreamingResponse
import json

@router.post("/chat")
async def chat(body: ChatRequest, _=Depends(get_current_user)):
    async def generate_stream():
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in body.history[-10:]   # cap at last 10 turns
        ]
        # Inject run context as system message
        ctx = await build_run_context(run, redis_client, log_lines=50)
        system_msg = build_system_prompt(ctx)
        messages = [{"role": "system", "content": system_msg}] + messages
        messages.append({"role": "user", "content": body.message})

        async for chunk in await llm_client.chat_stream(messages):
            # chunk["message"]["content"] is the token fragment
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield json.dumps({"token": token}) + "\n"
        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(generate_stream(), media_type="application/x-ndjson")
```

### Pattern 3: Frontend Streaming (Chat hook)

**What:** `fetch` + `ReadableStream` iteration to consume NDJSON tokens; update Zustand state per token.
**When to use:** `useAiStream` hook for `AiChatTab`.

```typescript
// Pattern: same host/token refresh approach as useLogStream.ts and useGradeStream.ts
// No new library needed — raw fetch with ReadableStream
export async function* streamChat(
  runId: string,
  message: string,
  history: ChatMessage[],
  token: string,
): AsyncGenerator<string> {
  const resp = await fetch("/api/v1/ai/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ run_id: runId, message, history }),
  });
  if (!resp.ok || !resp.body) throw new Error(`${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const obj = JSON.parse(line);
      if (obj.token) yield obj.token;
    }
  }
}
```

### Pattern 4: FastAPI Lifespan Warm-up

**What:** Use FastAPI `lifespan` context manager (already the standard in FastAPI 0.115) to call `warm_up()` at startup.
**When to use:** `main.py` lifespan — fires once when the backend container starts.

```python
# Source: FastAPI lifespan docs
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm the LLM model
    llm = get_llm_client()
    await llm.warm_up()
    yield
    # Shutdown: nothing needed

app = FastAPI(lifespan=lifespan)
```

### Pattern 5: Ollama Unavailability — 503 Handler

**What:** Catch `httpx.ConnectError` / `ollama.ResponseError` and return 503 with user-facing message.
**When to use:** Every AI endpoint. Wrap in a helper so the pattern is consistent.

```python
import httpx
import ollama as ollama_lib

async def safe_generate(llm_client, prompt: str, max_tokens: int = 1024) -> str:
    try:
        return await llm_client.generate(prompt, max_tokens)
    except (httpx.ConnectError, httpx.TimeoutException, ollama_lib.ResponseError) as exc:
        raise HTTPException(
            status_code=503,
            detail="AI assistant is currently unavailable. Contact your instructor if this persists.",
        ) from exc
```

### Anti-Patterns to Avoid

- **Sending GDS/DEF to any LLM client:** `context_builder.py` already enforces this; never add `artifact_path` to the context dict.
- **`stream=True` on explain/advisor endpoints:** Structured output (per-parameter card format) is harder to parse from a stream; wait-for-complete is correct here.
- **Ignoring `<think>` tags in deepseek-r1 responses:** The model emits `<think>...</think>` reasoning chains before the final answer. These must be stripped from explain/advisor responses. In chat, they may be shown or stripped; stripping is recommended for clarity.
- **Using a single `LLM_CLIENT` global without thread safety:** FastAPI is async; use a module-level singleton initialized once in lifespan, not per-request construction.
- **Passing full run log (thousands of lines) to Ollama:** `build_run_context` already caps at `log_lines` (default 100). For explain endpoints the caller should pass `log_lines=100`; for chat use `log_lines=50` (context budget).
- **Passing student email/name in any prompt:** `build_run_context` returns `design_name` from config, never user PII. Prompt templates must not inject `run.project.user.email` or similar.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP calls to Ollama | Custom httpx wrapper | `ollama` Python AsyncClient | Handles NDJSON streaming, retry, connection pooling; tested against Ollama API |
| NDJSON streaming in FastAPI | Custom chunked response | `StreamingResponse` with async generator | Built into FastAPI; handles Transfer-Encoding: chunked automatically |
| Frontend SSE auth | `EventSource` wrapper | Raw `fetch` + `ReadableStream` | EventSource cannot set Authorization header; project already uses raw fetch for WS |
| `<think>` tag stripping | Custom parser | `re.sub(r"<think>.*?</think>", "", ...)` with `re.DOTALL` | One regex; covers multiline reasoning blocks |
| Chat history trimming | Token counter | Last-N-turns slice (`history[-10:]`) | Ollama context is ~4K tokens default; 10 turns keeps well under limit |

**Key insight:** The entire AI backend is one pattern repeated 5 times: build context → format prompt → call Ollama → strip tags → return. The scaffolding is already in place. The hardest part is prompt quality, not infrastructure.

---

## Common Pitfalls

### Pitfall 1: deepseek-r1 `<think>` tags in response
**What goes wrong:** Response like `<think>Let me analyze the timing...</think>\n\nThe WNS of -2.3ns indicates...` is returned verbatim to the frontend, showing internal chain-of-thought noise.
**Why it happens:** deepseek-r1 distill models always emit reasoning traces before the answer.
**How to avoid:** `re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()` in `OllamaClient.generate()`.
**Warning signs:** Frontend shows `<think>` text; test with an actual deepseek-r1 response.

### Pitfall 2: Ollama default num_ctx too small
**What goes wrong:** Long ORFS logs get silently truncated in context; AI gives answer about wrong part of log.
**Why it happens:** Ollama's default `num_ctx` for deepseek-r1:7b is ~4096 tokens. 100 lines of ORFS log can easily exceed this.
**How to avoid:** Pass `options={"num_ctx": 8192}` for explain endpoints. 8192 is safe for the model on 8 GB VRAM. Alternatively, pre-filter log to last N ERROR/WARNING lines rather than raw tail.
**Warning signs:** AI references line numbers that don't exist in the provided excerpt; misses key error.

### Pitfall 3: Model cold-start on first request causes frontend timeout
**What goes wrong:** First request to `/ai/explain/log` after deployment takes 15-60 seconds as Ollama loads the model from disk; browser times out.
**Why it happens:** `keep_alive: -1` warm-up in `warm_up()` fixes this at backend startup. But if warm-up fails silently (Ollama not yet started), the first real request hits the same problem.
**How to avoid:** `warm_up()` must be called in FastAPI `lifespan` with a retry loop (3 attempts, 5-second backoff). Log success/failure clearly. Frontend shows "AI assistant loading..." on 503 response.
**Warning signs:** First AI request always slow; subsequent requests fast.

### Pitfall 4: Chat streaming fails behind Nginx proxy
**What goes wrong:** Nginx buffers the entire `StreamingResponse` before forwarding to browser; user sees no streaming, just a long wait then full response.
**Why it happens:** Nginx `proxy_buffering on` is the default.
**How to avoid:** Set `X-Accel-Buffering: no` response header on the `/ai/chat` endpoint. FastAPI `StreamingResponse` should include this header. Nginx respects it.
**Warning signs:** Chat streams fine in direct uvicorn testing but not behind Nginx in Docker Compose.

### Pitfall 5: ollama Python library version drift
**What goes wrong:** `ollama` library API changed between 0.1.x and 0.6.x; old examples use dict response access where new version uses attribute access or vice versa.
**Why it happens:** The library had breaking API changes in 2025.
**How to avoid:** Pin `ollama==0.6.1` in `pyproject.toml`. Use dict-style access (`response["response"]`) which is stable. Test with a real Ollama instance in integration tests, not mocks.
**Warning signs:** `KeyError: 'response'` or `AttributeError` on the response object.

### Pitfall 6: Frontend explain cache invalidation race
**What goes wrong:** User submits a new run; explain cache from old run is still shown; response panel shows explanation for previous run's log.
**Why it happens:** Zustand `aiSlice` caches explain results by `runId`; if `runId` doesn't change (shouldn't happen, but) or cache key is wrong.
**How to avoid:** Cache key in aiSlice must be `runId`. On new run submission, clear cache for old runId OR scope cache as `Map<runId, explainResult>`. Per CONTEXT.md: cache until new run is submitted.
**Warning signs:** Log explains show context from a different run.

### Pitfall 7: Config advisor with no run context gives hallucinated values
**What goes wrong:** Advisor called before any run exists; prompt has no PPA metrics; model makes up plausible-sounding but ungrounded values.
**Why it happens:** `build_run_context` returns `ppa: {}` when run has no metrics yet.
**How to avoid:** Prompt template must explicitly state "No run metrics available — providing general guidance" when `ppa` is empty. Frontend advisory panel should show a disclaimer when no run exists.
**Warning signs:** Advisor suggests `CLOCK_PERIOD=10` with no basis when user hasn't run anything.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Ollama API: Chat with history (multi-turn)
```python
# Source: ollama Python library 0.6.1 AsyncClient docs
async def chat_stream(self, messages: list[dict]) -> AsyncIterator:
    return await self._client.chat(
        model=self._model,
        messages=messages,
        stream=True,
        options={"num_ctx": 8192, "num_predict": 512},
        keep_alive=-1,
    )
```

### Ollama API: Model warm-up (keep_alive=-1)
```python
# Source: Ollama FAQ / docs.ollama.com/faq
# POST /api/generate with empty prompt and keep_alive=-1 pins model in VRAM
await self._client.generate(model=self._model, prompt="", keep_alive=-1)
```

### FastAPI lifespan (FastAPI 0.115 standard)
```python
# Source: FastAPI 0.115 lifespan docs
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_llm_client().warm_up()
    yield

app = FastAPI(lifespan=lifespan)
```

### Existing context_builder usage
```python
# Source: backend/app/ai/context_builder.py (existing scaffold)
ctx = await build_run_context(run, redis_client, log_lines=100)
# ctx keys: run_id, status, stage_completed, target_stage, ppa, config, log_tail, design_name
```

### Existing prompt registry usage
```python
# Source: backend/app/ai/prompts/__init__.py (existing scaffold)
from app.ai.prompts import PROMPT_REGISTRY, register_prompt

@register_prompt("explain_log")
def explain_log_prompt(ctx: dict) -> str:
    stage = ctx.get("stage_completed", "unknown")
    log = "\n".join(ctx["log_tail"][-80:])
    return (
        f"You are an expert ASIC design engineer helping a student debug an ORFS run.\n"
        f"Design: {ctx['design_name']}, PDK: sky130hd, Stage: {stage}\n"
        f"PPA: WNS={ctx['ppa'].get('worst_negative_slack')}, "
        f"DRC={ctx['ppa'].get('drc_routing_errors')}\n\n"
        f"Last 80 lines of ORFS log:\n{log}\n\n"
        f"Explain the errors in plain language. Be specific about which ORFS stage failed "
        f"and what the student can try. Avoid jargon — this is for a university student."
    )
```

### Zustand AI slice structure
```typescript
// Pattern: follows existing courseSlice.ts / jobSlice.ts pattern
export interface AiSlice {
  explainCache: Record<string, string>;   // runId → explain text (cleared on new run)
  advisorResult: AdvisorResult | null;
  chatHistory: ChatMessage[];             // last 10 turns, cleared on run switch
  chatStreaming: boolean;
  setExplainCache: (runId: string, text: string) => void;
  clearExplainCache: (runId: string) => void;
  setChatHistory: (history: ChatMessage[]) => void;
  appendChatToken: (token: string) => void;
  setChatStreaming: (v: boolean) => void;
  setAdvisorResult: (r: AdvisorResult | null) => void;
}
```

### X-Accel-Buffering header for Nginx streaming
```python
# Source: FastAPI docs + Nginx proxy_buffering behavior
return StreamingResponse(
    generate_stream(),
    media_type="application/x-ndjson",
    headers={"X-Accel-Buffering": "no"},
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requests` + sync Ollama | `ollama` AsyncClient with `stream=True` | 2025 (ollama lib 0.4+) | Native async; no thread blocking |
| `sse-starlette` for SSE | `StreamingResponse` + NDJSON | FastAPI 0.100+ | Simpler; no extra dep; same browser behavior |
| `python-jose` | `PyJWT` 2.10.x | Phase 1 decision | Already in project |
| `passlib` | `argon2-cffi` 25.x | Phase 1 decision | Already in project |
| FastAPI `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.95+ | `on_event` deprecated; lifespan is standard |

**Deprecated/outdated:**
- `@app.on_event("startup")`: Use `lifespan` context manager instead; deprecated in FastAPI 0.95, still works but will be removed.
- `ollama` library before 0.4.0: Completely different API shape. Pin to 0.6.1.
- `EventSource` for authenticated SSE: Cannot set headers; use `fetch` + `ReadableStream`.

---

## Open Questions

1. **deepseek-r1:7b `<think>` tags in streaming chat**
   - What we know: Streaming chat yields tokens including the `<think>` prefix tokens before the final answer
   - What's unclear: Should the frontend suppress `<think>...</think>` tokens in streaming display, or show them as a collapsible "reasoning" section?
   - Recommendation: Strip silently in the backend stream generator before yielding. Simpler, keeps frontend code clean.

2. **Ollama Docker Compose service startup ordering**
   - What we know: FastAPI lifespan calls `warm_up()` at startup; if Ollama container isn't ready, warm-up fails
   - What's unclear: `depends_on` in docker-compose.yml doesn't guarantee Ollama is ready (just started)
   - Recommendation: Implement warm-up as a retry loop (3 attempts, 5-second backoff) in `OllamaClient.warm_up()`. Log clearly on each attempt. Backend should still start even if Ollama is down (503 on actual AI requests is the correct behavior).

3. **num_ctx 8192 vs 4096 on DL380 Gen9**
   - What we know: DL380 Gen9 has tight CPU budget; deepseek-r1:7b needs ~4.7 GB storage + VRAM for inference
   - What's unclear: Whether the DL380 Gen9 has a GPU at all; if CPU-only inference, num_ctx doesn't affect VRAM
   - Recommendation: Document in deployment notes that Ollama runs on CPU if no CUDA GPU present; CPU inference is slow (~2-5 min per explain); GPU strongly recommended for usable latency. For CPU-only, reduce `num_predict` to 512 for explain endpoints.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `backend/pytest.ini` (asyncio_mode = auto) |
| Quick run command | `cd backend && uv run pytest tests/test_ai_routes.py -x -q` |
| Full suite command | `cd backend && uv run pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-01 | POST /ai/explain/log returns 200 with explanation text (mocked Ollama) | unit | `pytest tests/test_ai_routes.py::test_explain_log_returns_explanation -x` | ❌ Wave 0 |
| AI-01 | POST /ai/explain/timing returns 200 (mocked) | unit | `pytest tests/test_ai_routes.py::test_explain_timing_returns_explanation -x` | ❌ Wave 0 |
| AI-01 | POST /ai/explain/drc returns 200 (mocked) | unit | `pytest tests/test_ai_routes.py::test_explain_drc_returns_explanation -x` | ❌ Wave 0 |
| AI-01 | Ollama 503 returns user-facing error message | unit | `pytest tests/test_ai_routes.py::test_explain_log_ollama_unavailable -x` | ❌ Wave 0 |
| AI-01 | think tags stripped from response | unit | `pytest tests/test_ai_routes.py::test_think_tags_stripped -x` | ❌ Wave 0 |
| AI-02 | POST /ai/advisor/config returns parameter suggestions list | unit | `pytest tests/test_ai_routes.py::test_advisor_config_returns_suggestions -x` | ❌ Wave 0 |
| AI-02 | Advisor with empty PPA context returns generic suggestions | unit | `pytest tests/test_ai_routes.py::test_advisor_config_no_ppa_context -x` | ❌ Wave 0 |
| AI-03 | POST /ai/chat returns streaming NDJSON with tokens | unit | `pytest tests/test_ai_routes.py::test_chat_streams_tokens -x` | ❌ Wave 0 |
| AI-03 | Chat history capped at 10 turns | unit | `pytest tests/test_ai_routes.py::test_chat_history_capped -x` | ❌ Wave 0 |
| AI-03 | OllamaClient.warm_up() completes without error (mocked) | unit | `pytest tests/test_ai_routes.py::test_warm_up_succeeds -x` | ❌ Wave 0 |
| AI-03 | OllamaClient.warm_up() swallows exception gracefully | unit | `pytest tests/test_ai_routes.py::test_warm_up_handles_failure -x` | ❌ Wave 0 |
| AI-01,02,03 | All AI endpoints require auth (existing test) | unit | `pytest tests/test_ai_routes.py::test_ai_endpoints_require_auth -x` | ✅ |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/test_ai_routes.py -x -q`
- **Per wave merge:** `cd backend && uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ai_routes.py` — replace 501-stub tests with implementation tests; mock `OllamaClient` using `app.dependency_overrides` or `unittest.mock.AsyncMock`
- [ ] `tests/conftest.py` — add `mock_llm_client` fixture that returns `AsyncMock` responses for `generate()` and `chat_stream()`

*(Existing test infrastructure covers framework; only AI-specific test bodies and mock fixture need adding)*

---

## Sources

### Primary (HIGH confidence)
- `backend/app/ai/llm_client.py` — existing scaffold (class structure locked for Phase 3)
- `backend/app/ai/context_builder.py` — existing scaffold (context dict format confirmed)
- `backend/app/ai/prompts/__init__.py` — registry pattern confirmed
- `backend/app/api/routes/ai.py` — all 5 route signatures confirmed
- `frontend/src/hooks/useGradeStream.ts` — streaming pattern for chat hook
- `CLAUDE.md` §"AI Service — Prompt Templates", §"Environment Variables", §"Real ORFS Metrics Schema"
- [Ollama Python library 0.6.1](https://github.com/ollama/ollama-python) — AsyncClient, streaming, install
- [Ollama keep_alive / FAQ](https://docs.ollama.com/faq) — model warm-up, keep_alive=-1
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/tutorial/server-sent-events/) — SSE / streaming responses

### Secondary (MEDIUM confidence)
- [deepseek-r1 Ollama library page](https://ollama.com/library/deepseek-r1) — 7B = 4.7 GB, 128K context window (model card)
- WebSearch result: Ollama default num_ctx ~4096, can be set via `options={"num_ctx": 8192}`
- WebSearch result: deepseek-r1 `<think>...</think>` tag behavior, stripping recommendation

### Tertiary (LOW confidence)
- WebSearch: DL380 Gen9 GPU presence — not confirmed; deployment notes should address

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `ollama` lib 0.6.1 confirmed; FastAPI patterns from existing code
- Architecture: HIGH — all scaffolding already in codebase; patterns verified
- Pitfalls: HIGH — deepseek-r1 `<think>` tag and Ollama context window are documented behaviors; Nginx buffering is well-known

**Research date:** 2026-03-16
**Valid until:** 2026-06-16 (Ollama library stable; FastAPI stable; deepseek-r1 model behavior stable)
