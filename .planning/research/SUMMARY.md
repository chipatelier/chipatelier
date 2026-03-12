# Research Summary

**Project:** ChipAtelier
**Domain:** Web-based ASIC education platform (managed RTL-to-GDS, live logs, layout viewer, AI assistance)
**Researched:** 2026-03-12

---

## Key Findings

### Stack

All pre-decided choices in `CLAUDE.md` are validated. **Two security flags:**
- Replace `python-jose` (unmaintained, CVEs) → **`PyJWT 2.10.x`**
- Replace `passlib` (maintenance-only since 2020) → **`argon2-cffi 25.x`**

**New additions recommended:**
- `aioboto3` (async MinIO/S3 in FastAPI — never use sync boto3)
- `TanStack Query` (client-side server state for job polling)
- `openapi-typescript` + `openapi-fetch` (type-safe client from FastAPI's OpenAPI spec)
- `Radix UI` (accessible headless components)

**Current verified versions:** FastAPI 0.117.x, SQLAlchemy 2.0.43, Pydantic 2.11.9, redis-py 6.4.0, MapLibre GL 5.20.0, xterm.js 6.0.0, noVNC 1.6.0, Zustand 5.0.11, Vite 8.0.0

---

### Table Stakes (Must Have for Phase 1)

Features users expect — missing any makes the platform feel broken:

- Job submission (Verilog + config upload) + execution
- Live log streaming to browser terminal (WebSocket → xterm.js)
- Job status tracking + cancellation
- Static layout snapshot PNG (seconds, not minutes — fast-path forever)
- PPA metrics display (WNS, TNS, DRC count, area, power)
- Artifact download (GDS, DEF, reports)
- Run history per project
- User auth + project isolation per user
- Resource quota enforcement (cgroup limits per container)
- Stage-level progress stepper (derived from log streaming events)
- Storage usage visible to students ("1.2 GB of 5 GB used")

**VNC viewer** (noVNC → OpenROAD Qt GUI) is also Phase 1 — it's the biggest differentiator with the highest complexity. Do not slip it to Phase 2.

---

### Differentiators (Competitive Advantage)

No existing open-source platform combines all of these:

| Feature | Phase |
|---------|-------|
| Interactive tiled layout viewer (MapLibre GL + KLayout) | Phase 2 |
| VNC viewer tab (OpenROAD Qt GUI in browser) | Phase 1 |
| Click-to-inspect layout (OpenDB query API) | Phase 2 |
| Assignment system with locked/editable params | Phase 2 |
| Auto-grading on checkpoint rules (DRC=0, WNS targets) | Phase 2 |
| Anonymous leaderboard per assignment | Phase 2 |
| AI log explainer (local Ollama, design data on-prem) | Phase 3 |
| One-command Docker Compose deploy | Phase 1 |

---

### Architecture Patterns to Follow

1. **Container-per-job isolation** — `--network none --cap-drop ALL`; always clean up in `finally`
2. **Redis pub/sub for live logs** — LTRIM + TTL after job completes; disk for history
3. **Two-phase layout delivery** — fast-path PNG (seconds) first; tiles (2-5min) as separate background task; paths must never merge
4. **Dedicated Celery queues** — `orfs_jobs` (4 workers) + `background` (2 workers) as separate processes, not routing on shared workers
5. **VNC token = HMAC-signed JWT** — never proxy by session UUID; separate `VNC_TOKEN_SECRET`

**Recommended build order:**
1. Infrastructure (Docker Compose stack)
2. Database schema (Alembic migrations)
3. Auth (JWT endpoints)
4. Job submission → Celery → ORFS container
5. Log streaming (Redis pub/sub + WebSocket)
6. Artifact storage (MinIO)
7. Static layout PNG (fast-path KLayout)
8. Frontend shell (auth, project list, job view)
9. VNC integration (container lifecycle + Nginx token routing)
10. Tile pipeline (Phase 2: KLayout tiles + MapLibre GL viewer)

---

### Watch Out For

**Phase 1 Critical:**
- **Orphaned containers** after worker crash → watchdog Celery beat task every 5 min
- **Redis log memory exhaustion** → LTRIM + TTL on all log channels; `maxmemory-policy noeviction`
- **WebSocket silent drops** at Nginx 60s default timeout → keepalive pings + client reconnect with log history fetch
- **Celery single-queue starvation** → DEDICATED worker processes for `orfs_jobs` vs `background`; not routing modes
- **VNC token guessable** → HMAC-signed JWT, not session UUID
- **Fast-path PNG blocked by tile generation** → two completely separate code paths; PNG is NOT a precursor step to tiles

**Phase 2:**
- **PostgreSQL JSONB ordering wrong** for leaderboard → use functional B-tree index with `::numeric` cast, not GIN

**Phase 3:**
- **Ollama first-request hang** → warm model on service startup; streaming responses; 60s timeout

**Security always:**
- ORFS containers: `--network none --cap-drop ALL --read-only --user orfs:orfs`
- Access token in memory only (never localStorage); refresh token in httpOnly cookie
- Cloud LLMs must NEVER receive GDS/DEF contents or student PII

---

### Open Questions

1. `python-jose` → `PyJWT`: Verify all existing JWT code in spec uses standard claims only (no python-jose-specific extensions)
2. Competitor current state (Efabless, TinyTapeout) should be verified — research based on training data through Aug 2025; they may have added features
3. KLayout tile generation performance on DL380 Gen9: benchmark before Phase 2 ships to ensure background workers don't thrash CPU
4. Ollama model choice: `llama3.2` (3B/8B) for CPU-only; `codellama` for RTL-aware explanations — validate against real ORFS error logs

---

## Files

| File | Content |
|------|---------|
| `STACK.md` | Validated tech stack with versions, security flags, installation commands |
| `FEATURES.md` | Table stakes, differentiators, anti-features, dependency graph, competitor comparison |
| `ARCHITECTURE.md` | Component boundaries, data flow patterns, build order, anti-patterns |
| `PITFALLS.md` | 11 critical pitfalls with prevention strategies, phase mapping, security checklist |

---
*Synthesized: 2026-03-12*
