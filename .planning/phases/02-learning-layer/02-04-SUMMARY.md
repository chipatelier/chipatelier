---
phase: 02-learning-layer
plan: "04"
subsystem: grading
tags: [celery, redis, pubsub, fastapi, websocket, react, zustand, typescript, submissions]

requires:
  - phase: 02-01
    provides: "Submission ORM model, Assignment model with checkpoint_rules JSONB, Run model with ppa/config JSONB"
  - phase: 02-02
    provides: "Assignment endpoints (create, list, toggle open), course enrollment model"

provides:
  - "POST /assignments/{id}/submit — locked-param validation + Celery dispatch"
  - "GET /assignments/{id}/submissions/mine — all user submissions ordered by submitted_at desc"
  - "GET /assignments/{id}/preview-score — server-side checkpoint preview, no submission created"
  - "evaluate_checkpoint_rules() — pure function for hard gates + scored criteria + partial credit"
  - "evaluate_submission Celery task (background queue) — evaluates, writes DB, publishes grade:{run_id}"
  - "WS /ws/runs/{run_id}/grade/stream — single-message grade push with 300s timeout"
  - "useGradeStream.ts — WebSocket hook mirroring useLogStream pattern"
  - "CheckpointCards component — preview + result modes, hard gates + scored criteria + partial credit"
  - "AssignmentView component — Instructions/Submit/Leaderboard tab bar with grade flow"
  - "courseSlice.ts — Zustand slice for courses, assignments, submissions, grade results"
  - "submissions.ts — typed API client for submission endpoints"

affects:
  - "02-06 (leaderboard — reads submissions table, highest score per user per assignment)"
  - "02-05 (run comparison — can show is_submitted status from Run model)"

tech-stack:
  added: []
  patterns:
    - "Celery task imported inside route handler body (not top-level) to avoid circular imports — established in Phase 1, reinforced here"
    - "evaluate_checkpoint_rules as pure function (no DB, no Celery) — directly unit-testable without mocking"
    - "Grade WebSocket: single-message pattern — subscribe, receive one message, close (vs log stream which is continuous)"
    - "Preview vs result mode in CheckpointCards — client-side compute for preview, server result for graded display"

key-files:
  created:
    - backend/app/api/routes/submissions.py
    - backend/app/schemas/submissions.py
    - worker/tasks/checkpoint_eval.py
    - frontend/src/api/submissions.ts
    - frontend/src/store/courseSlice.ts
    - frontend/src/hooks/useGradeStream.ts
    - frontend/src/components/CheckpointCards/CheckpointCards.tsx
    - frontend/src/components/CheckpointCards/index.ts
    - frontend/src/components/AssignmentView/AssignmentView.tsx
    - frontend/src/components/AssignmentView/index.ts
  modified:
    - backend/app/api/websocket.py
    - backend/app/main.py
    - worker/tasks/__init__.py
    - frontend/src/store/index.ts
    - backend/tests/test_submissions.py
    - backend/tests/test_checkpoint_eval.py

key-decisions:
  - "evaluate_checkpoint_rules is a pure function (no DB, no Redis) — enables unit testing without mocking infrastructure; the Celery task calls it and handles all side effects"
  - "Grade WS uses single-message pattern (subscribe → receive one → close) vs log stream continuous pattern — grading is a one-shot event not a stream"
  - "Multiple submissions allowed (all stored) — GET /submissions/mine returns all; frontend shows best score; server does not enforce highest-score retention to avoid race conditions"
  - "worker/tasks/__init__.py updated with try/except import to support both production (from tasks import ...) and test (worker.tasks.checkpoint_eval) import paths"
  - "Preview endpoint (GET /preview-score) uses server-side evaluate_checkpoint_rules to ensure preview matches actual grading result — no client-side divergence"

patterns-established:
  - "Single-message WS pattern: subscribe to grade:{run_id}, push one JSON message, close — distinct from continuous log stream"
  - "Pure evaluation function pattern: business logic extracted from Celery task for unit testability"
  - "Locked param validation: compare str(actual) to str(required) to handle int/str JSONB round-trip"

requirements-completed:
  - COUR-04
  - COUR-05

duration: 9min
completed: 2026-03-15
---

# Phase 02 Plan 04: Submission and Auto-Grading Summary

**Checkpoint grading loop closed: POST /submit with locked-param validation, evaluate_submission Celery task with hard gates + partial credit, Redis grade publish to grade:{run_id}, grade WebSocket endpoint, and React CheckpointCards + AssignmentView with live preview and grade result display.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-15T08:38:53Z
- **Completed:** 2026-03-15T08:47:39Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments

- Submission route with locked-param mismatch validation returns 422 with human-readable errors
- `evaluate_checkpoint_rules()` pure function handles hard gates (block score=0), scored criteria, and partial credit thresholds — fully unit-tested
- Celery task dispatched inside handler body (not top-level import) to prevent circular imports
- Grade published to `grade:{run_id}` Redis channel (not `logs:{run_id}`)
- Grade WebSocket endpoint: validates JWT, subscribes to Redis, pushes single JSON message, closes
- CheckpointCards renders in preview mode (client-side compute) and result mode (from gradeResult)
- AssignmentView provides Instructions/Submit/Leaderboard tab bar; Submit tab handles full grade flow
- `useGradeStream` mirrors `useLogStream` pattern with proactive token refresh
- TypeScript: zero errors across all 10 new/modified files

## Task Commits

1. **Task 1: Submission route + checkpoint_eval Celery task** - `51db13f` (feat)
2. **Task 2: Frontend grade stream hook, CheckpointCards, AssignmentView, course store** - `b3eada9` (feat)

**Plan metadata:** (final commit below)

## Files Created/Modified

- `backend/app/api/routes/submissions.py` — POST /submit, GET /submissions/mine, GET /preview-score
- `backend/app/schemas/submissions.py` — SubmitRequest, SubmissionResponse, PreviewScoreResponse
- `backend/app/api/websocket.py` — Added grade_stream WS endpoint (grade:{run_id} channel)
- `backend/app/main.py` — Registered submissions router
- `worker/tasks/checkpoint_eval.py` — evaluate_checkpoint_rules (pure) + evaluate_submission Celery task
- `worker/tasks/__init__.py` — Added checkpoint_eval import with try/except for test compatibility
- `backend/tests/test_submissions.py` — 5 tests (locked param mismatch, multi-submit, Celery dispatch, preview, not-complete)
- `backend/tests/test_checkpoint_eval.py` — 5 tests (hard gate blocks, hard gate passes, partial credit, below threshold, JSON serializable)
- `frontend/src/api/submissions.ts` — submitRun, getMySubmissions, getPreviewScore with full types
- `frontend/src/store/courseSlice.ts` — Zustand slice for course, assignment, submission, grade state
- `frontend/src/store/index.ts` — Added CourseSlice to AppStore
- `frontend/src/hooks/useGradeStream.ts` — WS hook for grade result streaming
- `frontend/src/components/CheckpointCards/CheckpointCards.tsx` — Dual-mode checkpoint display
- `frontend/src/components/CheckpointCards/index.ts` — Barrel export
- `frontend/src/components/AssignmentView/AssignmentView.tsx` — Full assignment UI with grade flow
- `frontend/src/components/AssignmentView/index.ts` — Barrel export

## Decisions Made

- `evaluate_checkpoint_rules` is a pure function: no DB, no Redis — the Celery task handles all side effects. Enables isolated unit testing without mocking infrastructure.
- Grade WebSocket uses single-message pattern (subscribe → receive one JSON → close) vs log stream's continuous pattern — grading is a one-shot event.
- Multiple submissions stored without server-side score comparison — GET /submissions/mine returns all; frontend shows best. Avoids race conditions between concurrent submissions.
- `worker/tasks/__init__.py` uses try/except import to support both production CWD (`from tasks import ...`) and test suite path (`worker.tasks.checkpoint_eval`) without errors.
- Preview endpoint uses server-side `evaluate_checkpoint_rules` to guarantee preview matches actual grading result — no client-side divergence risk.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `worker/tasks/__init__.py` used `from tasks import ...` which fails when imported via `worker.tasks.*` path from tests. Fixed by wrapping imports in try/except (Rule 3 — blocking). Applied without interruption.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Grading loop is complete: students can submit, receive automated scores, and see checkpoint breakdown
- Leaderboard (plan 02-06) can read `submissions` table and join with `runs.ppa` for anonymous rankings
- Run comparison (plan 02-05) can use `run.is_submitted` status set by `evaluate_submission`

---
*Phase: 02-learning-layer*
*Completed: 2026-03-15*
