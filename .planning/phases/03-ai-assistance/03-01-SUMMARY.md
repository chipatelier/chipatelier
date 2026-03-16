---
phase: 03-ai-assistance
plan: "01"
subsystem: backend-ai
tags: [ollama, llm, prompts, testing, ai-foundation]
dependency_graph:
  requires: []
  provides:
    - OllamaClient with generate/chat_stream/warm_up
    - PROMPT_REGISTRY with 4 registered templates
    - Wave 0 test infrastructure for Phase 3
  affects:
    - backend/app/main.py (lifespan warm_up)
    - backend/app/api/routes/ai.py (consumed by Plan 03-02)
tech_stack:
  added:
    - ollama==0.6.1 (Python AsyncClient for Ollama inference)
  patterns:
    - register_prompt decorator auto-imports via __init__.py bottom imports
    - OllamaClient._client mocked by replacing attribute in unit tests
    - lifespan warm_up patched via app.ai.llm_client.get_llm_client in test_client fixture
key_files:
  created:
    - backend/app/ai/prompts/explain.py
    - backend/app/ai/prompts/advisor.py
    - backend/tests/ai/__init__.py
    - backend/tests/ai/conftest.py
    - backend/tests/ai/test_ollama_client.py
    - backend/tests/ai/test_context_builder.py
    - backend/tests/ai/test_prompt_registry.py
  modified:
    - backend/app/ai/llm_client.py (full rewrite of OllamaClient)
    - backend/app/ai/prompts/__init__.py (auto-import prompt modules)
    - backend/app/core/config.py (OLLAMA_MODEL field)
    - backend/app/main.py (lifespan warm_up)
    - backend/pyproject.toml (ollama dep, asyncpg upgrade)
    - backend/tests/conftest.py (mock get_llm_client in test_client fixture)
    - backend/tests/test_ai_routes.py (fix broken NotImplementedError stub test)
decisions:
  - asyncpg upgraded from 0.29.* to 0.30.* — 0.29 has no Python 3.13 wheel and fails to compile; 0.30 ships pre-built wheels for Python 3.13
  - test_client fixture patches app.ai.llm_client.get_llm_client (not app.main.get_llm_client) because lifespan uses a local import inside the function body
metrics:
  duration: 563s
  completed: "2026-03-16"
  tasks_completed: 2
  files_created: 7
  files_modified: 7
---

# Phase 3 Plan 01: AI Foundation Summary

**One-liner:** OllamaClient with deepseek-r1:7b support (think-tag stripping, 3-retry warm_up), 4 registered ORFS prompt templates, and Wave 0 test infrastructure with mocked Ollama fixtures.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | OllamaClient, prompt templates, OLLAMA_MODEL setting | 3f639ab | llm_client.py, prompts/explain.py, prompts/advisor.py, prompts/__init__.py, config.py, main.py, pyproject.toml |
| 2 | Wave 0 test infrastructure and unit tests | 252b86c | tests/ai/\*, tests/conftest.py, tests/test_ai_routes.py |

## What Was Built

### OllamaClient (backend/app/ai/llm_client.py)

Full implementation replacing the Phase 1 stub:
- `generate()`: calls `ollama.AsyncClient.generate()` with `stream=False`, `num_ctx=8192`, `keep_alive=-1`; strips `<think>...</think>` reasoning traces from deepseek-r1 output using `re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)`
- `chat_stream()`: calls `ollama.AsyncClient.chat()` with `stream=True`; returns async iterator of chunk dicts
- `warm_up()`: 3-retry loop with 5-second backoff using `asyncio.sleep(5)`; non-fatal on total failure (logs warning, model loads on first real request)

### Prompt Templates

Four templates registered in `PROMPT_REGISTRY` via `@register_prompt` decorator:

- **explain_log**: Last 80 log lines + stage + design name + WNS/DRC from ppa. Asks for plain-language explanation of errors with concrete fix suggestions.
- **explain_timing**: WNS, TNS, CLOCK_PERIOD, CORE_UTILIZATION; includes note about CTS ideal-clock removal for cts/route/finish stages.
- **explain_drc**: DRC error count, placement violations, utilization, place density; explains routing DRC causes and fixes.
- **advisor_config**: All 7 CURATED_PARAMS listed with current values; PPA metrics when available; "No run metrics available — providing general guidance" when ppa is empty. Requests structured output format: `PARAM: current -> suggested | Reason: explanation`.

### Settings

Added `OLLAMA_MODEL: str = "deepseek-r1:7b"` to `Settings` in `backend/app/core/config.py`. `get_llm_client()` now passes `model=settings.OLLAMA_MODEL`.

### FastAPI Lifespan

`backend/app/main.py` lifespan now calls `await llm.warm_up()` after DB init and storage bucket check.

### Test Infrastructure (Wave 0)

- `tests/ai/conftest.py`: `mock_llm_client` fixture (AsyncMock with canned responses), `sample_run_context` fixture
- `tests/ai/test_ollama_client.py`: 6 tests covering generate think-tag stripping, warm_up success/retry/failure
- `tests/ai/test_context_builder.py`: 7 tests covering keys, log capping, Redis failure, PII absence, bytes decoding
- `tests/ai/test_prompt_registry.py`: 12 tests covering registration, content, curated params, empty-PPA handling

## Verification Results

```
tests/ai/          — 26 passed
tests/test_ai_routes.py — 7 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] asyncpg==0.29.* fails to build on Python 3.13**
- **Found during:** Task 1 (first `uv add ollama` attempt)
- **Issue:** asyncpg 0.29.0 has no Python 3.13 pre-built wheel; C extension compilation fails against Python 3.13 `_PyLong_AsByteArray` API change
- **Fix:** Updated `pyproject.toml` to `asyncpg==0.30.*` which ships Python 3.13 wheels
- **Files modified:** backend/pyproject.toml, backend/uv.lock
- **Commit:** 3f639ab

**2. [Rule 3 - Blocking] test_client fixture triggers Ollama warm_up (15s timeout in tests)**
- **Found during:** Task 2 (running test_ai_routes.py)
- **Issue:** New lifespan warm_up calls real Ollama, which isn't available in test environment; 3 retries × 5s = 15s hang per test
- **Fix:** Updated `test_client` fixture in `tests/conftest.py` to patch `app.ai.llm_client.get_llm_client` with an AsyncMock that no-ops `warm_up()`
- **Files modified:** backend/tests/conftest.py
- **Commit:** 252b86c

**3. [Rule 1 - Bug] test_ollama_client_generate_raises_not_implemented no longer valid**
- **Found during:** Task 2 (test planning)
- **Issue:** The Phase 1 stub test asserted `NotImplementedError` from `OllamaClient.generate()`, which no longer applies after Phase 3 implementation
- **Fix:** Replaced with `test_ollama_client_is_instantiable` that verifies the object initializes correctly
- **Files modified:** backend/tests/test_ai_routes.py
- **Commit:** 252b86c

## Self-Check: PASSED

Files verified:
- backend/app/ai/llm_client.py — FOUND
- backend/app/ai/prompts/explain.py — FOUND
- backend/app/ai/prompts/advisor.py — FOUND
- backend/tests/ai/conftest.py — FOUND
- backend/tests/ai/test_ollama_client.py — FOUND
- backend/tests/ai/test_context_builder.py — FOUND
- backend/tests/ai/test_prompt_registry.py — FOUND

Commits verified:
- 3f639ab — FOUND (feat(03-01): implement OllamaClient...)
- 252b86c — FOUND (feat(03-01): create Wave 0 test infrastructure...)
