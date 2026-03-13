# Codebase Concerns

**Analysis Date:** 2026-03-13

## Tech Debt

**Silent failure on artifact download in ORFS job execution:**
- Issue: `_download_workspace()` in `worker/tasks/orfs_job.py` (lines 199-229) silently catches all exceptions and passes without logging details. If MinIO is unreachable or misconfigured, the job continues with an empty workspace, and the ORFS container fails with a cryptic error message.
- Files: `worker/tasks/orfs_job.py` (line 205-229)
- Impact: Students see confusing "missing input file" errors instead of understanding that artifact retrieval failed. Debugging connectivity issues is difficult.
- Fix approach: Log the exception at WARNING level with context. Consider retrying once with exponential backoff. Store download failure status in Run record.

**Excessive exception suppression in tile generation:**
- Issue: `generate_png()` task in `worker/tasks/tile_generator.py` wraps the entire PNG generation in a broad try/except that catches all exceptions and then attempts artifact upload fallback (lines 99-105). If KLayout crashes during rendering, the exception is logged but the task completes "successfully" from Celery's perspective.
- Files: `worker/tasks/tile_generator.py` (lines 99-105)
- Impact: Failed PNG generation is opaque to monitoring systems. Instrumentation on "completed tasks" masks systematic rendering failures that could indicate KLayout configuration issues.
- Fix approach: Distinguish between recoverable errors (KLayout not installed) and unrecoverable errors (crash). Fail the task explicitly on crashes so Celery dead-letter handling can trigger alerts. Install KLayout in worker image as a critical dependency.

**Silent container cleanup race on cancellation:**
- Issue: When a job is cancelled via `DELETE /jobs/{id}`, the code calls `_celery.control.revoke()` with SIGTERM but does NOT verify the container actually stops before returning success to the client. The watchdog task runs every 2 minutes, so there is a race window where a cancelled container continues running (or hangs) for up to 2 minutes.
- Files: `backend/app/api/routes/jobs.py` (lines 155-162), `worker/tasks/watchdog.py`
- Impact: Resource leaks if many jobs are cancelled in quick succession. Containers accumulate on the host. Students may observe stale processes continuing to consume CPU.
- Fix approach: In `cancel_job()`, immediately call `ContainerManager.stop_and_remove()` after revoke, or ensure watchdog runs every 30 seconds (currently 120s). Add explicit confirmation that container is stopped before returning 200 OK.

**Workspace cleanup depends on finally block in Celery context:**
- Issue: `worker/tasks/orfs_job.py` (lines 188-192) relies on the finally block to clean up `workspace` and the container. However, if the Celery worker process is killed (SIGKILL) during the task, the finally block does NOT execute, leaving orphaned directories in `/tmp/workspace_*` on the host and orphaned containers.
- Files: `worker/tasks/orfs_job.py` (lines 122-192)
- Impact: Long-running servers accumulate `/tmp` disk usage over weeks. Orphaned containers consume host resources. After a worker crash, the next deployment may inherit stale containers.
- Fix approach: Implement a separate periodic cleanup task (e.g., "cleanup-stale-workspaces" beat task) that scans for `/tmp/workspace_*` older than 6 hours and removes them. Add a HOST-level cron job to ensure cleanup even if the application is down.

**VNC session port allocation is not transactional:**
- Issue: In `backend/app/api/routes/vnc.py` (lines 33-47), `_find_available_port()` queries the database for used ports and selects an available one, but there is no locking. If two concurrent requests call `start_vnc_session()` simultaneously, they may both find the same port as available and create two sessions on the same port.
- Files: `backend/app/api/routes/vnc.py` (lines 33-47), and indirectly `backend/app/api/routes/vnc.py` (lines 129-142)
- Impact: Port collision causes unpredictable VNC viewer behavior. Second session may not be reachable, or traffic may be misrouted.
- Fix approach: Use database-level SELECT ... FOR UPDATE to lock the port range during allocation, or use Redis atomic operations (INCR) to allocate ports sequentially. Alternatively, pre-allocate ports at startup and use a lock-free queue.

**KLayout package dependency is optional but not surfaced:**
- Issue: `worker/tasks/tile_generator.py` (lines 59-72) gracefully handles missing KLayout by logging a warning and skipping PNG generation. However, the worker image Dockerfile may not include KLayout, and there is no health check or startup validation to ensure it's present. Students will silently get no layout preview without realizing it.
- Files: `worker/tasks/tile_generator.py` (lines 59-72), `worker/Dockerfile` (implied — not present in provided context)
- Impact: Essential feature (layout preview) silently degrades. Students may think a run failed because they see no PNG in the UI.
- Fix approach: Add KLayout as a required dependency in `worker/Dockerfile` and `pyproject.toml`. Add a startup health check in the background worker that attempts to import klayout and raises an exception if missing. Document the requirement in `.env.example`.

## Known Bugs

**Metrics parsing assumes metadata.json exists but handles missing file gracefully:**
- Symptoms: ORFS runs that fail before logging/metrics are generated will have `ppa=null` in the runs table. The UI will display "No metrics available" but this is by design (returns defaults). Not a bug per se, but worth noting for troubleshooting.
- Files: `backend/app/services/metrics_service.py` (lines 42-56)
- Trigger: ORFS job crashes before writing metadata.json (e.g., synthesis failure, PDK not found)
- Workaround: Check job logs via WS endpoint to diagnose the failure. Metrics are optional; the logs are the source of truth.

**Stage pattern matching may miss ORFS output variations:**
- Symptoms: Logs stream but stage separators do not appear, or appear at unexpected times. Stage_completed remains null even after a stage completes.
- Files: `worker/tasks/orfs_job.py` (lines 32-39), `backend/app/services/log_parser.py` (lines 19-26)
- Trigger: If ORFS version changes and log output format varies (e.g., "Beginning synthesis" instead of "Starting synthesis"), patterns will not match.
- Workaround: Check raw log output in Redis logbuf to verify actual ORFS stage markers. Update STAGE_PATTERNS regex as needed. Consider centralizing pattern definitions (currently duplicated across files).

**WebSocket token validation accepts query parameter (not header) — XSS risk:**
- Symptoms: The WS endpoint at `GET /api/v1/ws/jobs/{run_id}/logs/stream?token=...` accepts the JWT in the query string because WebSocket clients (browsers) cannot set custom headers. This exposes the token in browser history and server logs.
- Files: `backend/app/api/websocket.py` (lines 22-27)
- Trigger: Student opens the WS endpoint. Token appears in browser history, server access logs, and any proxy/firewall logs.
- Workaround: Ensure JWT_SECRET_KEY is rotated regularly. Use httpOnly cookies for main auth and reserve query-param tokens for WebSocket-only flows. Consider using a separate short-lived scoped token for log streaming.

## Security Considerations

**Docker socket mount on worker is a privilege escalation vector:**
- Risk: The orfs-worker service in `docker-compose.yml` (line 81) mounts `/var/run/docker.sock`, allowing the worker container to spawn and manage other containers. If the worker container is compromised, an attacker can run arbitrary containers with host privileges.
- Files: `docker-compose.yml` (line 81), `worker/container/manager.py` (line 31)
- Current mitigation: Worker runs as non-root inside container and uses Docker API with default permissions. ORFS containers are network-isolated and read-only. But this is defense-in-depth; the socket mount itself is a critical trust boundary.
- Recommendations: Document clearly in DEPLOYMENT.md that this approach is suitable only for on-premise, trusted environments. For production, consider rootless Docker or Podman. Alternatively, use a separate Docker daemon on a dedicated host and communicate via TCP (with TLS auth). Add runtime security monitoring (e.g., Falco) to detect suspicious container spawning.

**Environment variable defaults are unsafe in production:**
- Risk: `backend/app/core/config.py` has hardcoded defaults: `JWT_SECRET_KEY="change_me_in_production"`, `MINIO_SECRET_KEY="minioadmin"`. If `.env` is not provided, the application starts with known credentials.
- Files: `backend/app/core/config.py` (lines 21-25, 16-17)
- Current mitigation: `.env.example` in the repo should make operators aware they must set these. But no runtime check prevents starting with weak defaults.
- Recommendations: Add startup validation that raises an exception if JWT_SECRET_KEY or any sensitive field contains the default value. Require explicit override via environment variables. Document in README that deployment MUST provide a `.env` file with strong secrets.

**Log replay buffer has no access control beyond JWT token:**
- Risk: `GET /api/v1/jobs/{id}/logs` in `backend/app/api/routes/jobs.py` (lines 171-199) returns full log history from Redis after checking project ownership. However, logs may contain command-line arguments, file paths, or debug output that students should not see across projects. In a multi-course scenario, logs could leak information between courses.
- Files: `backend/app/api/routes/jobs.py` (lines 171-199), `worker/tasks/orfs_job.py` (lines 88-96)
- Current mitigation: Logs are scoped to a single run, and project ownership is verified. But a malicious instructor or unauthorized user with admin access could read any run's logs.
- Recommendations: Add granular audit logging for log access. Implement role-based filtering so instructors cannot read student logs from other courses. Consider encrypting sensitive portions of logs (e.g., config values).

**Celery task credentials are passed as args (task history is logged):**
- Risk: If sensitive data (API keys, PDK paths, etc.) is passed as task arguments in the future, Celery stores task history in Redis with full argument details. An attacker with Redis access can inspect task history.
- Files: `worker/celeryconfig.py` (lines 16-18)
- Current mitigation: Currently, only `run_id` is passed as an argument, which is not sensitive. But the pattern is established and could be misused.
- Recommendations: Never pass secrets as task arguments. Always fetch secrets from environment or database inside the task. If sensitive data must be task args, mask it in Celery task history (implement custom serializer).

## Performance Bottlenecks

**Tile generation is synchronous and can block background queue:**
- Problem: `generate_png()` task loads an entire GDS/DEF file into memory, renders a 2048x2048 PNG, and uploads it to MinIO — all synchronously. For large designs (>1000x1000 µm), this can take 5-30 seconds per run. If the background worker has only 2 concurrent slots and tile generation starts for multiple runs, the queue backs up.
- Files: `worker/tasks/tile_generator.py` (lines 20-112)
- Cause: Blocking I/O on file reads, KLayout rendering (single-threaded), and MinIO uploads. No async I/O or chunking.
- Improvement path: (1) Make PNG generation async using thread pool or multiprocessing. (2) Render directly to MinIO chunks instead of buffering entire PNG in memory. (3) Add priority queue so background tasks (tiles, AI hints) don't block urgent tasks (grading). (4) Profile actual ORFS designs to determine if the bottleneck is real.

**Database JSONB queries without indexes on hot keys:**
- Problem: Leaderboard queries (not shown in provided files) may scan the `ppa` JSONB column filtering on `worst_negative_slack` or `total_negative_slack`. Without a GIN index on the top-level keys, these queries do a full table scan.
- Files: `backend/app/models/run.py` (lines 37-39), potential queries in `backend/app/api/routes/` (not fully explored)
- Cause: JSONB requires explicit indexes. The SQLAlchemy model doesn't define GIN indexes (Alembic migration needed).
- Improvement path: (1) Add GIN index on the `ppa` column in a migration: `CREATE INDEX idx_runs_ppa_gin ON runs USING GIN (ppa)`. (2) Add expression indexes for hot keys: `CREATE INDEX idx_runs_wns ON runs ((ppa->>'worst_negative_slack'::double precision))`. (3) Benchmark leaderboard queries to confirm improvement.

**Log buffer is trimmed to 5000 lines — large jobs may lose history:**
- Problem: `LOG_BUFFER_MAX = 5000` in `worker/tasks/orfs_job.py` (line 45). A synthesis job that runs for 4+ hours may produce 20,000+ log lines. Only the last 5000 are kept in Redis. Late-joining students will see truncated history.
- Files: `worker/tasks/orfs_job.py` (line 45)
- Cause: Redis memory efficiency concern — keeping unlimited lines can exhaust memory on large runs.
- Improvement path: (1) Increase LOG_BUFFER_MAX to 10,000 or 20,000 and profile memory usage. (2) Stream old logs to MinIO after job completion and read from there on late joins (requires backend change to fetch from S3 instead of only Redis). (3) Compress log buffer in Redis using gzip. (4) Monitor actual run log volumes to set an appropriate threshold.

**Redis connection pool is global and never resized:**
- Problem: `backend/app/core/redis.py` creates a single ConnectionPool at module import time. If traffic spikes, all requests share the same pool size. Pool is never garbage-collected or resized.
- Files: `backend/app/core/redis.py` (lines 9-15, 26-28)
- Cause: Pool size is fixed at default (10 connections). High concurrency may exhaust the pool and cause timeouts.
- Improvement path: (1) Make pool size configurable via `REDIS_POOL_SIZE` env var. (2) Monitor pool usage in production and alert if utilization exceeds 80%. (3) Consider switching to connection pooling with auto-scaling (e.g., redis-py-cluster or Dragonfly).

## Fragile Areas

**Stage transition detection is sensitive to log format changes:**
- Files: `worker/tasks/orfs_job.py` (lines 32-39), `backend/app/services/log_parser.py` (lines 19-26)
- Why fragile: The regex patterns are calibrated against one ORFS version. If the toolchain output format changes (e.g., from "Starting synthesis" to "Opening synthesis"), stage detection breaks silently. Patterns are duplicated across two files.
- Safe modification: (1) Centralize STAGE_PATTERNS in a shared module. (2) Add logging to track unmatched lines in first 200 lines of each job (early warning system for pattern drift). (3) Add acceptance tests with real ORFS output samples (or mock samples). (4) Document stage pattern calibration process.
- Test coverage: `backend/tests/test_log_parser.py` should test pattern matching against representative ORFS output from multiple versions. Currently no test samples shown.

**VNC session lifecycle has implicit state machine (no transitions validated):**
- Files: `backend/app/api/routes/vnc.py`, `worker/tasks/vnc_session.py`, `backend/app/models/vnc_session.py` (not fully read)
- Why fragile: VNC sessions have states `starting`, `running`, `stopped`, but transitions are not validated. A session can move from `stopped` back to `starting` if a new task is dispatched. No database constraint enforces valid transitions.
- Safe modification: (1) Add explicit state machine validation in VncSession model. (2) Add a `status_transition_history` audit log. (3) Fail explicitly if transition is invalid. (4) Document all valid transitions in the model docstring.
- Test coverage: `backend/tests/test_vnc.py` should cover invalid transitions and concurrent requests.

**Job cancellation does not guarantee immediate cleanup:**
- Files: `backend/app/api/routes/jobs.py` (lines 127-164), `worker/tasks/watchdog.py`
- Why fragile: When a job is cancelled, the status is updated to `cancelled` and Celery revoke is called. But the container may not stop immediately if the ORFS process is stuck in a system call. The watchdog will eventually clean it up, but there is a window where a "cancelled" run still has an active container.
- Safe modification: (1) Implement a "hard stop" after 30 seconds if SIGTERM doesn't work (kill -9 or docker kill). (2) Add a `cancel_requested_at` timestamp and watchdog checks for stale cancel requests. (3) Add explicit confirmation to the user that the container is stopped before returning success.
- Test coverage: Simulate SIGTERM-resistant containers (strace -p) and verify they are eventually killed.

**MinIO endpoint configuration is not validated at startup:**
- Files: `backend/app/core/config.py`, `worker/tasks/orfs_job.py`, `backend/app/services/storage_service.py`
- Why fragile: If `MINIO_ENDPOINT` is unreachable or the credentials are wrong, the application starts without error. First upload or download will fail cryptically.
- Safe modification: Add a startup health check in `backend/app/main.py` that connects to MinIO and verifies the bucket exists. Raise an exception on startup if health check fails.
- Test coverage: `backend/tests/test_artifacts.py` should include tests with unreachable MinIO.

## Scaling Limits

**PostgreSQL connection pool is not configurable:**
- Current capacity: Async engine uses default pool size (usually 10 connections). No config exposed.
- Limit: At ~100 concurrent users with multiple async operations per user, connections exhaust and requests queue with timeouts.
- Scaling path: (1) Add `DATABASE_POOL_SIZE` and `DATABASE_POOL_RECYCLE` to config. (2) Use connection pooling middleware (e.g., PgBouncer) in production. (3) Monitor pool usage via prometheus metrics.

**Redis can become a bottleneck for log streaming at scale:**
- Current capacity: Single Redis instance handles both Celery broker and pubsub for log streaming. At ~50 concurrent WebSocket clients receiving log lines at 100 Hz, Redis CPU is the limiting factor.
- Limit: ~100-200 concurrent log streams before Redis CPU hits 80%.
- Scaling path: (1) Separate Redis instances for broker vs. pubsub (Redis does not need to replicate the same data across both roles). (2) Use Redis Cluster for horizontal scaling of pubsub. (3) Implement client-side log buffering so UI doesn't request every single line (aggregate in batches). (4) Profile actual production log rates.

**VNC port range is fixed 6080-6099 (20 ports max):**
- Current capacity: MAX_VNC_SESSIONS environment variable caps concurrent sessions, default 8. But port range is hardcoded to 20 ports.
- Limit: Cannot spawn more than 20 VNC containers due to port exhaustion, even if RAM permits.
- Scaling path: (1) Make port range configurable. (2) Use dynamic port allocation (OS chooses port, Nginx uses an upstream list instead of fixed ports). (3) Use container networking instead of host port mapping (Docker Compose services can communicate directly on any port).

**Celery queue depth is unbounded:**
- Current capacity: No limits on task queue depth. If 100 jobs are queued but workers are busy, all 100 are stored in Redis memory.
- Limit: Queue size depends on available Redis RAM. At 1KB per queued task, 1GB Redis can queue ~1M tasks. But this causes slow pubsub and broker responsiveness.
- Scaling path: (1) Add per-user rate limiting: max N jobs queued per student. (2) Implement backpressure: reject new job submissions if queue depth > threshold. (3) Use persistent task storage (PostgreSQL or RabbitMQ) instead of only Redis. (4) Monitor queue depth and alert on growth.

## Dependencies at Risk

**ORFS container image is pinned to `openroad/orfs:latest`:**
- Risk: `latest` tag is a moving target. A new ORFS release could break the flow. Conversely, `latest` is never auto-updated unless explicitly pulled, creating staleness.
- Files: `backend/app/core/config.py` (line 28: `ORFS_IMAGE: str = "openroad/orfs:latest"`)
- Impact: Inconsistent behavior across deployments. New deployments may get different ORFS version than existing ones. A breaking change in ORFS could fail all new jobs mid-semester.
- Migration plan: (1) Pin to a specific version tag (e.g., `openroad/orfs:2024.09`). (2) Test version upgrades in a canary phase before rolling to production. (3) Store reference metrics in `.github/workflows/orfs-canary.yml` (implied by CLAUDE.md but not shown in provided files). (4) Document version constraints in README.

**KLayout Python API is optional and may not be available in worker image:**
- Risk: If KLayout is not installed in the worker Dockerfile, PNG generation silently skips. Students don't get layout previews and may assume the job failed.
- Files: `worker/tasks/tile_generator.py` (lines 59-72), inferred in worker/Dockerfile (not provided)
- Impact: Essential feature is silently degraded. No alert to operators or users.
- Migration plan: (1) Add KLayout to `worker/Dockerfile` as a required system package. (2) Add a startup health check that fails loudly if KLayout is missing. (3) Document KLayout as a required dependency in README and `.env.example`.

**Redis is single-point-of-failure for broker and pubsub:**
- Risk: If Redis goes down, all jobs in queue are lost (no persistence by default). All active log streams disconnect.
- Files: `backend/app/core/redis.py`, `docker-compose.yml` (line 17)
- Impact: High availability is not possible without Redis Sentinel or Cluster. A Redis crash causes full application outage.
- Migration plan: (1) Enable Redis persistence (RDB snapshotting) in docker-compose.yml. (2) For production, use Redis Sentinel (HA) or Cluster (sharding). (3) Document backup/recovery procedures.

## Missing Critical Features

**No retry logic for transient failures:**
- Problem: If a container fails to spawn due to temporary Docker daemon issues, the task fails permanently. No exponential backoff or retry.
- Blocks: Students cannot resubmit jobs without manually creating a new run.
- Recommendation: Implement Celery task retry with exponential backoff (max 3 retries, 10-60 second delays). Distinguish between transient errors (Docker daemon busy) and fatal errors (invalid config).

**No quota enforcement on disk or runtime:**
- Problem: A student can submit unlimited jobs or run designs that consume the entire /data/artifacts volume, starving other students.
- Blocks: Resource isolation between users.
- Recommendation: Implement per-user storage quota (e.g., 10GB) and per-job runtime limit (already has JOB_TIMEOUT_SECONDS, but not enforced per-user). Track quota usage and reject submissions if limit reached.

**No monitoring or alerting on job failures:**
- Problem: If 10 jobs fail in a row due to a bug, operators are not alerted. Instructors must check the leaderboard to discover issues.
- Blocks: Proactive issue detection.
- Recommendation: Add Prometheus metrics for job success/failure rates and stage transition latencies. Set up alerts if failure rate exceeds 5% or if logs stop appearing for 10 minutes.

## Test Coverage Gaps

**Orphaned container cleanup is untested under SIGKILL conditions:**
- What's not tested: If Celery worker receives SIGKILL while run_orfs_job is executing, the finally block does not run. The workspace and container are orphaned.
- Files: `worker/tasks/orfs_job.py`, `worker/tasks/watchdog.py`
- Risk: Accumulation of orphaned resources in long-running deployments.
- Recommendation: Add integration test that simulates worker kill (`kill -9 <worker_pid>`) and verifies watchdog cleans up containers within 2 minutes.

**WebSocket late-join with expired log buffer:**
- What's not tested: If a student joins the log stream after 24 hours, the buffer has expired from Redis. The endpoint should gracefully return an empty buffer, not crash.
- Files: `backend/app/api/websocket.py` (lines 50-54)
- Risk: 500 error on late-join.
- Recommendation: Add test that waits 24 hours and then opens a WebSocket. Verify graceful empty-buffer response. (Or mock time using `freezegun`.)

**Concurrent VNC session start on same run:**
- What's not tested: Two students (or same student in two browser tabs) simultaneously call `POST /vnc/start/{run_id}`. Currently, idempotency is checked, but race conditions on port allocation are possible.
- Files: `backend/app/api/routes/vnc.py` (lines 33-161)
- Risk: Port collision or multiple sessions for same run.
- Recommendation: Add test with concurrent requests to `start_vnc_session()` and verify only one session is created or idempotency is correct.

**Database transaction isolation under concurrent updates:**
- What's not tested: Multiple background tasks attempt to update the same Run record simultaneously (e.g., orfs_job updating stage_completed while tile_generator updates artifact_path). Race conditions are possible if isolation level is not set correctly.
- Files: `backend/app/models/run.py`, potential concurrent writes in `worker/tasks/orfs_job.py` and `worker/tasks/tile_generator.py`
- Risk: Lost updates or inconsistent state.
- Recommendation: Verify PostgreSQL isolation level is `SERIALIZABLE` or use pessimistic locking in SQLAlchemy. Add test with concurrent updates and verify final state is correct.

---

*Concerns audit: 2026-03-13*
