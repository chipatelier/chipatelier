# Pitfalls Research

**Domain:** Web-based ASIC education platform (container orchestration, live streaming, layout visualization)
**Researched:** 2026-03-12
**Confidence:** HIGH — pitfalls derived from CLAUDE.md explicit warnings + known failure modes for this class of system

## Critical Pitfalls

### Pitfall 1: Orphaned ORFS Containers After Worker Crash

**Warning signs:** `docker ps` shows containers named `orfs_job_*` after no running jobs; disk usage climbing
**Prevention:**
- Always clean up in `finally` block — even on Celery task failure/timeout
- Watchdog Celery beat task (every 5 min): query DB for `status=running` jobs with no heartbeat > 2min → `docker rm -f` + mark job as `failed`
- Two-layer heartbeat: ORFS container heartbeat (to Redis, every 30s) AND Celery worker heartbeat (separate key)

**Phase:** Phase 1 — implement before production load

---

### Pitfall 2: Redis Memory Exhaustion From Log Streaming

**Warning signs:** Redis `INFO memory` shows steadily growing `used_memory`; OOM errors during heavy job load
**Prevention:**
- Apply `LTRIM logs:{run_id} 0 9999` after each PUBLISH (keep last 10k lines in Redis)
- Set TTL on log channels: `EXPIRE logs:{run_id} 86400` after job completes
- Redis `maxmemory-policy noeviction` (not `allkeys-lru`) — never silently drop log lines
- Store log history to disk in 100-line batches; Redis is live-only

**Phase:** Phase 1 — configure before first production jobs

---

### Pitfall 3: WebSocket Silent Drops at Nginx Timeout

**Warning signs:** Log terminal goes silent mid-job; client never reconnects; no error shown
**Prevention:**
- Send WebSocket keepalive ping every 30s from FastAPI endpoint
- Configure Nginx: `proxy_read_timeout 3600s; proxy_send_timeout 3600s;`
- Implement client-side reconnect with exponential backoff (max 30s)
- On reconnect: fetch log history from DB, resume from last line index, re-subscribe to Redis channel

**Phase:** Phase 1 — critical for 2-hour ORFS jobs

---

### Pitfall 4: Celery Single-Queue Starvation

**Warning signs:** Tile generation never runs while jobs are active; grading delayed for hours
**Prevention:**
- Two separate Celery worker processes — not routing modes on the same workers:
  ```
  celery -A worker worker -Q orfs_jobs -c 4     # dedicated
  celery -A worker worker -Q background -c 2    # dedicated
  ```
- Never use `task_routes` with a single worker process to solve this

**Phase:** Phase 1 — configure in docker-compose.yml from the start

---

### Pitfall 5: Docker Socket Security — Worker Container Escape

**Warning signs:** N/A (security concern, not runtime failure)
**Prevention:**
- ORFS containers always run with `--network none --cap-drop ALL --security-opt no-new-privileges --read-only --user orfs:orfs`
- Document the Docker socket mount risk clearly in README
- Consider rootless Docker or Podman for hardened deployments (mention in docs, not required for MVP)
- Never mount Docker socket inside ORFS containers — they must not be able to spawn containers

**Phase:** Phase 1 — security critical before any multi-user deployment

---

### Pitfall 6: VNC Session Token = Session UUID

**Warning signs:** VNC sessions accessible by guessing/enumerating UUIDs
**Prevention:**
- VNC token = HMAC-signed JWT with `VNC_TOKEN_SECRET` (separate from main JWT secret)
- Token payload: `{session_id, run_id, user_id, exp: now+2hr}`
- Nginx validates token signature before proxying — never proxy by session UUID alone

**Phase:** Phase 1 — implement correctly from the start

---

### Pitfall 7: Fast-Path PNG Blocked by Tile Generation

**Warning signs:** Layout preview unavailable for minutes after job completes
**Prevention:**
- Fast-path PNG generation is a synchronous KLayout call directly in Celery task immediately after ORFS completes (~seconds)
- Tile generation is a SEPARATE background Celery task dispatched after PNG is ready
- Never chain them: `generate_png.si() | generate_tiles.si()` — PNG must complete first, tiles are async
- Keep fast-path PNG logic forever — do NOT remove after Phase 2 ships tiles

**Phase:** Phase 1 (PNG) + Phase 2 (tiles) — paths must stay separate

---

### Pitfall 8: Celery Task Heartbeat vs Worker Heartbeat Conflated

**Warning signs:** Jobs marked as timed-out when worker is actually healthy; or zombie jobs when worker crashes
**Prevention:**
- **Worker heartbeat:** Celery's built-in `worker_heartbeat` (default 2s) — used for worker health in Flower/monitoring
- **Job heartbeat:** Custom Redis key `job_heartbeat:{run_id}` updated every 30s by ORFS task — used for orphan detection
- Watchdog uses job heartbeat (not worker heartbeat) to detect stuck jobs

**Phase:** Phase 1

---

### Pitfall 9: MinIO Multipart Upload Orphans

**Warning signs:** MinIO storage usage growing faster than artifact count; old incomplete uploads accumulating
**Prevention:**
- Always call `abort_multipart_upload` on exception in `finally` block
- Set MinIO lifecycle rule: abort incomplete multipart uploads after 24h
- Use MinIO Console to check `Incomplete Multipart Uploads` bucket metric

**Phase:** Phase 1

---

### Pitfall 10: PostgreSQL JSONB Wrong Index for PPA Ordering

**Warning signs:** Leaderboard queries slow (>100ms) with 1000+ runs; `EXPLAIN` shows sequential scan on `ppa` column
**Prevention:**
- GIN index on `ppa` column helps `@>` containment queries but NOT ordering/comparison
- For leaderboard queries that order by `ppa->>'worst_negative_slack'`, use functional B-tree index:
  ```sql
  CREATE INDEX idx_runs_wns ON runs ((( ppa->>'worst_negative_slack')::numeric));
  CREATE INDEX idx_runs_clock ON runs (((config->>'CLOCK_PERIOD')::numeric));
  ```
- Never order by JSONB text path without the `::numeric` cast — text ordering of numbers is wrong

**Phase:** Phase 2 — before leaderboard feature ships

---

### Pitfall 11: Ollama First-Request Hang

**Warning signs:** First AI request takes 10-60s; students see timeout; model not pre-loaded
**Prevention:**
- Warm Ollama model on service startup: `POST /api/generate {"model": "llama3.2", "prompt": "hello", "stream": false}`
- Use streaming responses for long AI outputs — don't wait for full completion
- Set 60s timeout on Ollama requests (not default which may be shorter)
- Log slow Ollama responses — if >10s, model needs warming again (restart recovery)

**Phase:** Phase 3 — implement in AI service startup

---

## Technical Debt Patterns

| Pattern | What Happens | Prevention |
|---------|-------------|------------|
| Sync DB queries in async FastAPI | Event loop blocked; concurrency collapses | Always use `async with session` + `await session.execute()` |
| Pydantic v1 models mixed with v2 | Silent validation failures; hard-to-debug schema drift | Pin to v2 from project start; never import from `pydantic.v1` |
| Alembic `--autogenerate` blindly applied | Drops columns, renames tables incorrectly | Always review generated migrations; never auto-apply to production |
| Hardcoded `localhost` in container config | Works in dev; breaks in Docker Compose networking | Use service names (`postgres`, `redis`, `minio`) as hostnames |
| Access token in localStorage | XSS extractable; auth bypass | Access token in memory only; refresh token in httpOnly cookie |
| Celery `task_always_eager=True` in tests | Hides async/queue behavior; masks real failures | Test with real Redis or mock at the service layer |
| Static asset URLs without content hash | Browser caches stale JS/CSS after deployment | Vite handles this automatically with `build.assetsDir` |
| ORFS image tagged `latest` in production | Silent breaking update mid-semester | Pin to specific digest; canary CI before bumping |

## Performance Traps

| Trap | Symptom | Fix |
|------|---------|-----|
| N+1 queries in run list endpoint | Slow project/run list pages with many runs | Use SQLAlchemy `selectinload` or JOIN; never loop and query |
| Uncompressed log storage | Disk fills with repetitive ORFS text logs | gzip logs in MinIO; typical ORFS log: 50MB → 5MB |
| Tile serving via FastAPI (not MinIO direct) | Tile requests bottleneck on Python app | Serve tiles from MinIO presigned URLs or configure Nginx to proxy MinIO directly |
| WebSocket per-connection log replay | 1000 lines replayed per reconnect × many students | Paginate history endpoint; client requests from last-seen line index |
| Celery result backend in Redis | Result data accumulates; Redis memory grows | Use `result_expires=3600`; or disable result backend for fire-and-forget tasks |
| KLayout tile generation in-process | Blocks Celery worker thread | KLayout Python in subprocess with timeout; not inline in task |

## Security Mistakes

| Mistake | Risk | Correct Approach |
|---------|------|-----------------|
| JWT secret in code or git | Token forgery if repo leaked | `JWT_SECRET_KEY` from `.env` only; never in `settings.py` default |
| ORFS container with `--network bridge` | Container can reach internal services | Always `--network none`; PDKs via volume mount only |
| Student Verilog executed as root | Privilege escalation via crafted RTL | `--user orfs:orfs` always; `--cap-drop ALL` |
| VNC token in URL query string | Token logged in Nginx access logs | Token in URL path segment (`/vnc/{token}`), not query param; Nginx log sanitization |
| Missing rate limiting on auth endpoints | Brute-force password attack | Rate limit `/api/v1/auth/login`: 5 req/min per IP |
| Instructor sees other students' data | Privacy violation | Row-level filtering on all queries: `WHERE user_id = current_user.id` or course enrollment check |
| Cloud LLM receives student PII | Data privacy violation | Strip student names/emails before AI context; never send GDS/DEF to cloud LLM |

## "Looks Done But Isn't" Checklist

- [ ] Job marked `complete` in DB but container still running → check finally block
- [ ] Log streaming works for short jobs but drops on 2hr jobs → test with full ORFS flow
- [ ] Tile viewer shows tiles but MapLibre GL shows blank on first load → check CORS headers on MinIO
- [ ] VNC opens but shows black screen → Xvfb not ready; supervisord startup order matters
- [ ] Assignment submission accepted but grade not stored → checkpoint_eval task silently failed; add error handling
- [ ] Leaderboard shows incorrect ordering → JSONB text vs numeric comparison bug
- [ ] Storage usage counter stale → `storage_used_bytes` needs atomic increment on artifact upload

## Pitfall-to-Phase Mapping

| Pitfall | Phase | Priority |
|---------|-------|----------|
| Orphaned containers (P1) | Phase 1 | Critical |
| Redis log memory (P2) | Phase 1 | Critical |
| WebSocket Nginx timeout (P3) | Phase 1 | Critical |
| Celery queue starvation (P4) | Phase 1 | Critical |
| Docker socket security (P5) | Phase 1 | Critical |
| VNC token security (P6) | Phase 1 | Critical |
| Fast-path PNG isolation (P7) | Phase 1/2 | High |
| Celery heartbeat distinction (P8) | Phase 1 | High |
| MinIO multipart orphans (P9) | Phase 1 | Medium |
| PostgreSQL JSONB indexing (P10) | Phase 2 | High |
| Ollama first-request warmup (P11) | Phase 3 | Medium |

---
*Pitfalls research for: ChipAtelier ASIC education platform*
*Researched: 2026-03-12*
