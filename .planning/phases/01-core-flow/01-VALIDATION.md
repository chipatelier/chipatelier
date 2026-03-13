---
phase: 1
slug: core-flow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24.x (backend); Vitest 2.x (frontend) |
| **Config file** | `backend/pytest.ini` — Wave 0 gap |
| **Quick run command** | `pytest backend/tests/ -x -q --tb=short` |
| **Full suite command** | `pytest backend/tests/ -v --cov=app --cov-report=term-missing && cd frontend && npm test` |
| **Estimated runtime** | ~30s quick / ~2 min full |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/ -x -q --tb=short`
- **After every plan wave:** Run `pytest backend/tests/ -v --cov=app --cov-report=term-missing && cd frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| AUTH-01 | 01-02 | 2 | AUTH-01 | integration | `pytest backend/tests/test_auth.py::test_register -x` | Wave 0 | ⬜ pending |
| AUTH-02 | 01-02 | 2 | AUTH-02 | integration | `pytest backend/tests/test_auth.py::test_login_returns_jwt_and_cookie -x` | Wave 0 | ⬜ pending |
| AUTH-03 | 01-02 | 2 | AUTH-03 | integration | `pytest backend/tests/test_auth.py::test_logout_invalidates_refresh -x` | Wave 0 | ⬜ pending |
| AUTH-04 | 01-02 | 2 | AUTH-04 | integration | `pytest backend/tests/test_auth.py::test_refresh_token -x` | Wave 0 | ⬜ pending |
| JOB-01 | 01-03 | 3 | JOB-01 | integration | `pytest backend/tests/test_jobs.py::test_project_create_and_upload -x` | Wave 0 | ⬜ pending |
| JOB-02 | 01-03 | 3 | JOB-02 | unit (mock Docker) | `pytest backend/tests/test_container.py::test_container_resource_limits -x` | Wave 0 | ⬜ pending |
| JOB-03 | 01-04 | 4 | JOB-03 | integration | `pytest backend/tests/test_websocket.py::test_log_stream -x` | Wave 0 | ⬜ pending |
| JOB-04 | 01-04 | 4 | JOB-04 | unit | `pytest backend/tests/test_log_parser.py::test_stage_detection -x` | Wave 0 | ⬜ pending |
| JOB-05 | 01-03 | 3 | JOB-05 | integration (mock Docker) | `pytest backend/tests/test_jobs.py::test_cancel_job -x` | Wave 0 | ⬜ pending |
| RSLT-01 | 01-05 | 5 | RSLT-01 | unit | `pytest backend/tests/test_metrics.py::test_parse_ppa -x` | Wave 0 | ⬜ pending |
| RSLT-02 | 01-05 | 5 | RSLT-02 | integration (mock S3) | `pytest backend/tests/test_artifacts.py::test_presigned_urls -x` | Wave 0 | ⬜ pending |
| RSLT-03 | 01-05 | 5 | RSLT-03 | unit (mock KLayout) | `pytest backend/tests/test_tile_generator.py::test_png_generation -x` | Wave 0 | ⬜ pending |
| RSLT-04 | 01-05 | 5 | RSLT-04 | integration | `pytest backend/tests/test_projects.py::test_run_history -x` | Wave 0 | ⬜ pending |
| LAYT-01 | 01-06 | 6 | LAYT-01 | unit | `pytest backend/tests/test_vnc.py::test_vnc_token_creation -x` | Wave 0 | ⬜ pending |
| DASH-04 | 01-02 | 2 | DASH-04 | integration | `pytest backend/tests/test_users.py::test_storage_usage -x` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pytest.ini` — asyncio_mode = "auto", testpaths, markers
- [ ] `backend/tests/conftest.py` — async_engine, session rollback fixture, TestClient, mock_s3, mock_docker, mock_redis fixtures
- [ ] `backend/tests/test_auth.py` — stubs for AUTH-01 through AUTH-04
- [ ] `backend/tests/test_jobs.py` — stubs for JOB-01, JOB-05
- [ ] `backend/tests/test_container.py` — stubs for JOB-02
- [ ] `backend/tests/test_websocket.py` — stubs for JOB-03
- [ ] `backend/tests/test_log_parser.py` — stubs for JOB-04
- [ ] `backend/tests/test_metrics.py` — stubs for RSLT-01
- [ ] `backend/tests/test_artifacts.py` — stubs for RSLT-02
- [ ] `backend/tests/test_tile_generator.py` — stubs for RSLT-03
- [ ] `backend/tests/test_projects.py` — stubs for RSLT-04
- [ ] `backend/tests/test_vnc.py` — stubs for LAYT-01
- [ ] `backend/tests/test_users.py` — stubs for DASH-04
- [ ] Framework: `uv add --dev pytest pytest-asyncio anyio httpx moto[s3]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live log stream visible in browser xterm.js terminal | JOB-03 | WebSocket end-to-end requires running containers | Submit a test job, observe live output in browser |
| VNC tab opens OpenROAD GUI with DEF pre-loaded | LAYT-01 | Requires display server + noVNC container | Launch VNC session on completed run, verify GUI shows design |
| Static layout PNG visible within seconds of job completion | RSLT-03 | Requires KLayout running in worker | Complete a test job, verify PNG appears in UI within 10s |
| cgroup limits enforced on ORFS container | JOB-02 | Host-level validation on RHEL 9 with cgroup v2 | Run job, inspect `docker stats`, verify CPU/RAM caps |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
