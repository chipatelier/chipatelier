---
phase: 3
slug: ai-assistance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/ai/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (unit), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ai/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | AI-01 | unit | `uv run pytest tests/ai/test_ollama_client.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | AI-01 | unit | `uv run pytest tests/ai/test_context_builder.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | AI-01 | unit | `uv run pytest tests/ai/test_prompt_registry.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | AI-01 | integration | `uv run pytest tests/ai/test_warmup.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | AI-02 | unit | `uv run pytest tests/ai/test_explain_routes.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | AI-02 | unit | `uv run pytest tests/ai/test_advisor_routes.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | AI-03 | unit | `uv run pytest tests/ai/test_chat_routes.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | AI-03 | integration | `uv run pytest tests/ai/test_chat_streaming.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/ai/__init__.py` — test package init
- [ ] `backend/tests/ai/conftest.py` — shared fixtures (mock OllamaClient, sample run context, mock DB session)
- [ ] `backend/tests/ai/test_ollama_client.py` — stubs for AI-01 (OllamaClient.generate, think-tag stripping, streaming)
- [ ] `backend/tests/ai/test_context_builder.py` — stubs for AI-01 (build_run_context with log/metrics/config)
- [ ] `backend/tests/ai/test_prompt_registry.py` — stubs for AI-01 (PROMPT_REGISTRY keys, template rendering)
- [ ] `backend/tests/ai/test_warmup.py` — stubs for AI-01 (model warm-up retry loop)
- [ ] `backend/tests/ai/test_explain_routes.py` — stubs for AI-02 (/explain/log, /explain/timing, /explain/drc)
- [ ] `backend/tests/ai/test_advisor_routes.py` — stubs for AI-02 (/advisor/config PPA-aware suggestions)
- [ ] `backend/tests/ai/test_chat_routes.py` — stubs for AI-03 (/chat multi-turn, context injection)
- [ ] `backend/tests/ai/test_chat_streaming.py` — stubs for AI-03 (NDJSON streaming, X-Accel-Buffering header)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ollama never sends GDS/DEF/PII to cloud | AI-01 | Requires network traffic inspection | Run with `LLM_BACKEND=ollama`, verify no outbound requests to external IPs via `tcpdump` or network policy |
| deepseek-r1:7b `<think>` tags stripped in UI | AI-01 | End-to-end visual verification | Trigger explain endpoint, verify no `<think>` tags appear in browser response |
| Model warm on startup eliminates first-request hang | AI-01 | Timing measurement | Cold-start backend, immediately call `/explain/log`, measure response time < 5s |
| Chat maintains multi-turn context coherence | AI-03 | Semantic quality judgment | Ask follow-up questions referencing prior answers, verify coherent context |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
