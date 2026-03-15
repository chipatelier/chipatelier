# Phase 2: Learning Layer - Research

**Researched:** 2026-03-15
**Domain:** Course/assignment management, auto-grading, config editing, click-to-inspect layout query, leaderboard/comparison/instructor dashboard
**Confidence:** HIGH (most domains well-understood from Phase 1 codebase; one area flagged LOW)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Assignment creation interface**
- Form wizard, not YAML upload — step-by-step: design + PDK → locked/editable param picker → checkpoint rule builder → due date
- Locked/editable params selected via checkbox list showing the curated safe subset from CLAUDE.md (CORE_UTILIZATION, PLACE_DENSITY, TNS_END_PERCENT, CLOCK_PERIOD, CORE_ASPECT_RATIO, CORE_MARGIN, SETUP_SLACK_MARGIN)
- Checkpoint rules authored via rule builder UI: pick metric from dropdown → pick operator (≥, =, ≤) → enter value → pick 'hard gate' or 'scored'. No JSON authoring required.
- Locked params require setting the forced value in the form (e.g. CLOCK_PERIOD=10). Passed as Make CLI args at job invocation — highest priority, overrides student config.mk.
- 1 assignment per course. Instructors clone/copy for reuse across sections.
- Assignment visibility: hidden until instructor explicitly opens it (not auto-released on enrollment)
- Multiple submissions allowed up to due date; system keeps the highest score

**Config editor form mode**
- Guided form mode: each editable param gets label + description + number input + valid range indicator (e.g. "CORE_UTILIZATION: 20–80")
- Locked params visible in form mode with their forced value and a "Locked by instructor" badge — shown greyed out, not hidden
- Mode switch: Form / Raw toggle in the Config tab header (not separate tabs, not hidden behind a link)
- Form mode available even without assignment enrollment — shows all curated params with no locked params in that context

**Grading feedback UX**
- On submission: optimistic "Submitted — grading in progress..." banner on the run; Celery task runs async; results pushed via existing WebSocket when complete
- Grade breakdown: inline checkpoint cards — each shows metric name, target, actual value, pass/fail, and points earned. Hard gates show checkmark/cross. Scored criteria show "WNS: 40/40 pts" or "20/40 pts (partial credit)".
- Score location: shown in the Assignments panel only (not on the run history table). Run history table shows "Submitted" status.
- Live checkpoint preview in Results tab BEFORE submission: shows how the run would score against the active assignment's checkpoint rules. Student sees "DRC: 0 checkmark", "WNS: -0.3 cross (need >= -0.1)" before clicking Submit.

**Leaderboard + run comparison**
- Anonymity: student sees their own name highlighted in their row; all other students shown as rank number only
- Sort: primary = total checkpoint score; tiebreaker = WNS
- Leaderboard lives inside each assignment: assignment detail view has tabs — Instructions | Submit | Leaderboard
- Run comparison: side-by-side metrics table — runs as columns, metrics as rows. Highlights better/worse values with color (green/yellow/red). Student checks 2-4 runs from their run history. Metrics shown: WNS, TNS, DRC violations, core utilization, total power, CLOCK_PERIOD (and other config.mk params that vary across selected runs).

**Click-to-inspect layout**
- Student clicks directly on the layout PNG image; click coordinates sent to the click-to-inspect API
- Results displayed in a right-side sidebar panel that slides in alongside the layout — persists until dismissed
- Info shown per element: cell instance name, cell type/master, net name(s), layer
- On miss (empty space): "No element at this location" message in the sidebar panel
- Existing LayoutSnapshot component extended to handle click events and coordinate mapping

**Course enrollment and navigation**
- New "Courses" section in main sidebar nav after enrollment (separate from personal Projects section)
- Inside course: Assignments list. Each assignment has tabs: Instructions | Submit | Leaderboard
- Submission flow: student opens assignment → clicks "Submit a Run" → modal picker shows eligible completed runs from their projects
- No assignment-dedicated project auto-created on enrollment; student submits any completed run from any personal project
- Locked param enforcement at submission validation time: backend checks run's config.mk has locked param values matching the assignment. Rejected with clear error if mismatch.

**Instructor dashboard**
- Primary view: per-student progress table (rows = students; columns: name, run count, last run status, submission status, score). Sortable.
- Actions: view only + CSV export of scores. No manual grade override in Phase 2.
- Queue info: queue depth (jobs waiting) + running jobs count + recent failures. Simple operational view.
- Dashboard lives inside course page as a "Dashboard" tab (alongside "Assignments" and "Students" tabs)

### Claude's Discretion
- Empty state design for Courses section before enrollment
- Exact visual styling for the checkpoint preview cards in Results tab
- Instructor assignment list / course page layout details
- Error state handling for submission validation failures
- CSV export format details
- Click-to-inspect coordinate scaling between rendered PNG size and design micron coordinates

### Deferred Ideas (OUT OF SCOPE)
- ORFS canary CI hardening (pin + canary workflow)
- GF180 / ASAP7 PDK support
- Manual grade override by instructor
- KLayout tiled interactive viewer (MapLibre GL)
- VNC "suspended" state (container pause/resume)
- Three-tier design library
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COUR-01 | Instructor can create an assignment with design, PDK, target stage, locked params, editable params, checkpoint rules, and due date | Assignment model schema, JSONB checkpoint_rules structure, param picker pattern |
| COUR-02 | Instructor can create a course and generate an enrollment code (format: VLSI-YYYY-XXXX, collision-checked) | Enrollment code generation pattern, collision detection via DB unique constraint |
| COUR-03 | Student can enroll in a course by entering an enrollment code | Enrollment model, code lookup + course_enrollments table |
| COUR-04 | Student can submit a completed run against an assignment for grading | Submission model, locked-param validation at submission time, highest-score retention |
| COUR-05 | System automatically evaluates checkpoint rules after submission (hard gates + scored with partial credit) | Celery checkpoint_eval task, .delay() dispatch from submission endpoint, Redis publish grade push |
| EDIT-01 | User can edit config.mk parameters in guided form mode with locked param enforcement | Monaco @monaco-editor/react, param metadata registry, locked field greying |
| EDIT-02 | User can edit config.mk in raw Monaco editor mode | @monaco-editor/react raw mode, same editor instance mode-switched |
| LAYT-02 | User can query layout element details by coordinates via click-to-inspect API | OpenDB Python subprocess approach, ODB file loading, linear inst scan for coordinate hit |
| DASH-01 | Student can see anonymous leaderboard for an assignment showing PPA rankings | PostgreSQL functional B-tree index on (ppa->>'worst_negative_slack')::numeric, anonymous display |
| DASH-02 | User can compare metrics across multiple runs in a side-by-side view | Run comparison component, ppa + config JSONB columns already stored |
| DASH-03 | Instructor can view class-wide dashboard: per-student counts, submission status, grade distribution, queue depth | Instructor-role gate, aggregation queries on submissions + runs, Redis queue depth via Celery inspect |
</phase_requirements>

---

## Summary

Phase 2 adds the educational layer on top of the Phase 1 job pipeline. The backend adds four new entity types — courses, assignments, submissions, and enrollments — each following the established FastAPI route file per entity with `Depends(get_current_user)` pattern. The checkpoint evaluation is a new Celery task dispatched via `.delay()` in the submission endpoint, which then publishes grade results to Redis so the existing WebSocket infrastructure can push them to the browser without a new WebSocket endpoint. The config editor gains Monaco editor with two modes (form/raw toggle) in a single component. Click-to-inspect requires running OpenROAD as a subprocess to load the ODB file and perform a linear scan of instances by bounding box — no native spatial index exists in OpenDB for Python, so the approach is to call `openroad -python` as a subprocess. The leaderboard uses functional B-tree indexes on extracted JSONB values with `::numeric` cast for ordering, which already exist or need migration from GIN to B-tree for the ordering use case.

**Primary recommendation:** Follow Phase 1 patterns strictly — new route files per entity, Zustand slices, Celery task on background queue, Redis pubsub for grade push. The click-to-inspect query endpoint is the only novel technical area requiring subprocess coordination with OpenROAD.

---

## Standard Stack

### Core (unchanged from Phase 1 — verified from codebase)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | from Phase 1 | Route handlers for courses, assignments, submissions | Already established; all auth patterns set |
| SQLAlchemy async | from Phase 1 | ORM for new models (Course, Assignment, Submission, Enrollment) | JSONBCompatible TypeDecorator already handles JSONB |
| Alembic | from Phase 1 | Migration 0003 for course/assignment/submission/enrollment tables | Established migration chain |
| Celery | from Phase 1 | checkpoint_eval task on `background` queue | dedicated background-worker already running |
| Redis | from Phase 1 | Grade push notifications via pubsub (`grade:{run_id}` channel) | Same pattern as log streaming |
| Pydantic | from Phase 1 | Schemas for new entities | End-to-end typed pattern |

### New Frontend Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @monaco-editor/react | ^4.x | Config editor raw Monaco mode (EDIT-02) | Official React wrapper; no webpack plugin needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| secrets (stdlib) | Python stdlib | Enrollment code random segment generation | For safe random alphanumeric, not uuid |
| openroad (subprocess) | ORFS container | Click-to-inspect ODB query | Run as subprocess inside ORFS container image |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openroad subprocess | opendbpy standalone pip | opendbpy pip package not reliably available outside ORFS container; subprocess approach reuses existing ORFS image |
| functional B-tree index for ORDER BY | GIN index | GIN supports containment queries; functional B-tree with `::numeric` cast is needed for ORDER BY (leaderboard). Both are needed — different index types serve different queries |

**Installation (frontend only):**
```bash
npm install @monaco-editor/react
```

---

## Architecture Patterns

### New Database Tables (Alembic migration 0003)

```sql
-- Course with enrollment code
CREATE TABLE courses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instructor_id   UUID NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    term            TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    enrollment_code TEXT UNIQUE NOT NULL,  -- VLSI-YYYY-XXXX format
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_courses_enrollment_code ON courses(enrollment_code);

-- Enrollment join table
CREATE TABLE course_enrollments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(course_id, user_id)
);

-- Assignment (1 per course, cloned for reuse)
CREATE TABLE assignments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id           UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    pdk                 TEXT NOT NULL DEFAULT 'sky130hd',
    target_stage        TEXT NOT NULL DEFAULT 'route',
    locked_params       JSONB NOT NULL DEFAULT '{}',   -- {"CLOCK_PERIOD": "10", ...}
    editable_params     JSONB NOT NULL DEFAULT '[]',   -- ["CORE_UTILIZATION", ...]
    checkpoint_rules    JSONB NOT NULL DEFAULT '{}',   -- hard[] + scored[] arrays
    due_at              TIMESTAMPTZ,
    is_open             BOOLEAN NOT NULL DEFAULT FALSE, -- hidden until instructor opens
    orfs_version        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Submission (one per student per assignment attempt; highest score retained)
CREATE TABLE submissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id       UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id),
    run_id              UUID NOT NULL REFERENCES runs(id),
    checkpoint_results  JSONB,   -- per-criterion results
    score               NUMERIC,
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Leaderboard ordering indexes (B-tree for ORDER BY, not GIN)
CREATE INDEX idx_runs_wns ON runs ((ppa->>'worst_negative_slack'));
CREATE INDEX idx_runs_wns_numeric ON runs (((ppa->>'worst_negative_slack')::numeric));
CREATE INDEX idx_submissions_score ON submissions (assignment_id, score DESC NULLS LAST);
```

### Recommended Project Structure (new files only)

```
backend/app/
  api/routes/
    courses.py          # COUR-01, COUR-02, COUR-03 — course CRUD + enrollment code
    assignments.py      # COUR-01 — assignment CRUD under course
    submissions.py      # COUR-04, COUR-05 — submit run, trigger grading, leaderboard
    query.py            # LAYT-02 — click-to-inspect endpoint
  models/
    course.py
    assignment.py
    submission.py
    enrollment.py
  schemas/
    courses.py
    assignments.py
    submissions.py

worker/tasks/
  checkpoint_eval.py    # COUR-05 — evaluate checkpoint rules, publish grade

frontend/src/
  components/
    ConfigEditor/
      ConfigEditor.tsx        # EDIT-01, EDIT-02 — form/raw toggle
      ParamForm.tsx           # form mode: curated params with ranges
      ParamMetadata.ts        # param descriptions, ranges, display labels
    CourseNav/                # sidebar course section (COUR-03)
    AssignmentView/           # tabs: Instructions | Submit | Leaderboard (COUR-04, DASH-01)
    CheckpointCards/          # checkpoint preview + grade breakdown (COUR-05)
    RunComparison/            # side-by-side metrics (DASH-02)
    InstructorDashboard/      # class view, CSV export (DASH-03)
    LayoutSnapshot/           # extend existing: click handler + inspect sidebar (LAYT-02)
  store/
    courseSlice.ts            # course/assignment/submission state
  api/
    courses.ts
    assignments.ts
    submissions.ts
    query.ts                  # click-to-inspect API call
  hooks/
    useGradeStream.ts         # WebSocket for grade push (reuses useLogStream pattern)
```

### Pattern 1: Enrollment Code Generation (COUR-02)

**What:** Generate a human-readable, collision-safe code in `VLSI-YYYY-XXXX` format.
**When to use:** `POST /api/v1/courses` endpoint on course creation.

```python
# Source: CLAUDE.md "Resolved Design Decisions" + Python stdlib
import secrets
import string
from datetime import datetime

SAFE_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "")

def generate_enrollment_code() -> str:
    year = datetime.utcnow().year
    segment = "".join(secrets.choice(SAFE_ALPHABET) for _ in range(4))
    return f"VLSI-{year}-{segment}"

async def create_enrollment_code_unique(db: AsyncSession) -> str:
    """Generate and retry until unique (collision-checked via DB unique constraint)."""
    for _ in range(10):
        code = generate_enrollment_code()
        existing = await db.execute(select(Course).where(Course.enrollment_code == code))
        if existing.scalar_one_or_none() is None:
            return code
    raise RuntimeError("Failed to generate unique enrollment code after 10 attempts")
```

### Pattern 2: Checkpoint Evaluation Celery Task (COUR-05)

**What:** After submission, evaluate hard gates and scored criteria against run's ppa JSONB.
**When to use:** Dispatched from submission endpoint via `.delay()` to `background` queue.

```python
# Source: CLAUDE.md checkpoint_rules schema + established Celery pattern from tile_generator.py
# In worker/tasks/checkpoint_eval.py
@app.task(name="tasks.checkpoint_eval.evaluate_submission", queue="background")
def evaluate_submission(submission_id: str) -> None:
    """Evaluate checkpoint rules and publish grade result via Redis pubsub."""
    import redis
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    ...
    # Fetch submission + run.ppa + assignment.checkpoint_rules from DB
    # Evaluate hard gates (all must pass for any score)
    # Evaluate scored criteria (accumulate points, check partial credit thresholds)
    # Write checkpoint_results + score to submissions table
    # Publish grade to Redis: r.publish(f"grade:{run_id}", json.dumps(result))
    # Update runs.is_submitted = True
```

**Celery dispatch in submission endpoint:**
```python
# Source: established pattern from orfs_job.py dispatch in jobs.py
from tasks.checkpoint_eval import evaluate_submission  # imported inside handler body
evaluate_submission.delay(str(submission.id))
```

### Pattern 3: Grade Push via WebSocket (COUR-05)

**What:** Reuse the Redis pubsub → WebSocket pattern for grade push.
**When to use:** After `evaluate_submission` task publishes to `grade:{run_id}`.

The existing WebSocket endpoint at `/api/v1/ws/jobs/{run_id}/logs/stream` is for log lines only. Add a second WebSocket endpoint for grade notifications:

```
WS /api/v1/ws/runs/{run_id}/grade/stream
```

Pattern is identical to `websocket.py`: validate JWT → subscribe Redis `grade:{run_id}` channel → push single JSON message on receipt → close. Frontend hook `useGradeStream.ts` mirrors `useLogStream.ts`.

### Pattern 4: Locked Param Enforcement at Submission (COUR-04)

**What:** Validate run's `config` JSONB matches assignment's `locked_params` before accepting submission.
**When to use:** `POST /api/v1/submissions` endpoint.

```python
# Source: CLAUDE.md locked params logic
async def validate_locked_params(run: Run, assignment: Assignment) -> list[str]:
    """Return list of violation messages, empty means valid."""
    errors = []
    locked = assignment.locked_params or {}  # e.g. {"CLOCK_PERIOD": "10"}
    run_config = run.config or {}
    for param, required_value in locked.items():
        actual = run_config.get(param)
        if str(actual) != str(required_value):
            errors.append(
                f"{param} must be {required_value} — your run used {actual}"
            )
    return errors
```

### Pattern 5: Leaderboard Query (DASH-01)

**What:** Order submissions by score DESC, then by WNS (from run.ppa) as tiebreaker. Anonymize.
**When to use:** `GET /api/v1/assignments/{id}/leaderboard`.

```python
# Source: CLAUDE.md "Known Constraints" — functional B-tree index, not GIN, for ORDER BY
# Migration must CREATE INDEX idx_runs_wns_numeric ON runs (((ppa->>'worst_negative_slack')::numeric));
stmt = (
    select(Submission, Run, User)
    .join(Run, Submission.run_id == Run.id)
    .join(User, Submission.user_id == User.id)
    .where(Submission.assignment_id == assignment_id)
    .order_by(Submission.score.desc().nullslast(), text("(runs.ppa->>'worst_negative_slack')::numeric DESC NULLS LAST"))
)
# Anonymize: return user_id (for caller to check against their own), never name/email
```

### Pattern 6: Click-to-Inspect via OpenROAD Subprocess (LAYT-02)

**What:** Run `openroad -python` as subprocess with an inline script that loads the ODB file and scans instances by bounding box around the clicked point.
**When to use:** `GET /api/v1/query/{run_id}?x_um=&y_um=&tolerance_um=`

**Critical finding:** OpenDB documentation explicitly states "The data model does not support a region query." This means there is no native spatial index in the Python API. The implementation must iterate all instances in the block and check each instance's bounding box against the query point.

```python
# Source: OpenROAD docs (openroad.readthedocs.io/en/latest/main/src/odb/README.html)
# OpenDB Python API — available methods: getInsts(), getBBox(), getMaster(), getName(), getITerms()
# Subprocess approach required: openroad binary is inside ORFS container, not in backend Python env

QUERY_SCRIPT_TEMPLATE = """
import openroad
import odb
import json
import sys

db = odb.dbDatabase.create()
odb.read_db(db, "{odb_path}")
chip = db.getChip()
block = chip.getBlock()
dbu = block.getDbUnitsPerMicron()

x_dbu = int({x_um} * dbu)
y_dbu = int({y_um} * dbu)
tol_dbu = int({tolerance_um} * dbu)

results = []
for inst in block.getInsts():
    bbox = inst.getBBox()
    if (bbox.xMin() - tol_dbu <= x_dbu <= bbox.xMax() + tol_dbu and
        bbox.yMin() - tol_dbu <= y_dbu <= bbox.yMax() + tol_dbu):
        master = inst.getMaster()
        nets = [it.getNet().getName() for it in inst.getITerms() if it.getNet()]
        results.append({{
            "name": inst.getName(),
            "master": master.getName() if master else None,
            "bbox": {{"xmin": bbox.xMin(), "ymin": bbox.yMin(),
                      "xmax": bbox.xMax(), "ymax": bbox.yMax()}},
            "nets": nets,
        }})

print(json.dumps(results))
"""

# Execute inside a temporary ORFS container (read-only workspace mount)
# openroad binary is at /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
```

**Coordinate mapping (PNG click to microns):**
The layout PNG is rendered by KLayout at a fixed pixel canvas (2048x2048). The design bounding box in microns must be stored at artifact upload time (from `block.getBBox()` in the generate_png task) as `layout_bbox` in the run record. Then:

```python
x_um = (click_x_px / png_width_px) * (bbox_xmax_um - bbox_xmin_um) + bbox_xmin_um
y_um = (1 - click_y_px / png_height_px) * (bbox_ymax_um - bbox_ymin_um) + bbox_ymin_um  # Y inverted
```

### Pattern 7: Config Editor Form/Raw Toggle (EDIT-01, EDIT-02)

**What:** Single component with two modes controlled by a state variable. Monaco for raw, custom form for guided.
**When to use:** Config tab in the main portal.

```typescript
// Source: @monaco-editor/react documentation (monaco-react.surenatoyan.com)
import Editor from "@monaco-editor/react";

// CURATED_PARAMS from CLAUDE.md safe subset
const CURATED_PARAMS: ParamMeta[] = [
  { key: "CORE_UTILIZATION", label: "Core Utilization", min: 20, max: 80, unit: "%" },
  { key: "PLACE_DENSITY", label: "Place Density", min: 0.3, max: 0.9, unit: "" },
  { key: "TNS_END_PERCENT", label: "TNS End Percent", min: 0, max: 100, unit: "%" },
  { key: "CLOCK_PERIOD", label: "Clock Period", min: 1, max: 100, unit: "ns" },
  { key: "CORE_ASPECT_RATIO", label: "Core Aspect Ratio", min: 0.5, max: 2.0, unit: "" },
  { key: "CORE_MARGIN", label: "Core Margin", min: 1, max: 20, unit: "µm" },
  { key: "SETUP_SLACK_MARGIN", label: "Setup Slack Margin", min: 0, max: 1, unit: "ns" },
];

// Locked params from assignment: { CLOCK_PERIOD: "10" }
// In form mode: render locked params greyed out with "Locked by instructor" badge
// Raw Monaco: readOnly decoration on locked param lines (or full editor if no assignment)
```

### Anti-Patterns to Avoid

- **Separate WebSocket endpoint for grade push:** Reuse Redis pubsub pattern. Do not build a polling mechanism — push via WebSocket like log streaming.
- **GIN index for leaderboard ORDER BY:** GIN indexes cannot be used for `ORDER BY` on extracted JSONB values. Functional B-tree index with `::numeric` cast is required.
- **opendbpy pip package standalone:** Do not attempt to install opendbpy outside the ORFS container. The Python bindings are built against ORFS's specific OpenROAD binary and are not pip-installable separately. Use subprocess into the ORFS container.
- **Eager evaluation of checkpoint preview:** The client-side checkpoint preview (before submission) should compute from the run's existing `ppa` JSONB plus the assignment's `checkpoint_rules` fetched on component mount. Do not call a submission endpoint — it is a display-only calculation.
- **Merging ppa and config columns:** These are separate JSONB columns by deliberate Phase 1 design decision. Keep separate for query clarity (leaderboard filters on ppa; param comparison filters on config).
- **Auto-releasing assignments on enrollment:** Assignments are hidden by default (`is_open = FALSE`). Instructor explicitly opens them. Never auto-open on enrollment.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Monaco editor React integration | Custom textarea with syntax highlight | @monaco-editor/react | Handles lazy loading, worker threads, dark theme |
| JWT validation in new WS endpoint | Custom token parser | Reuse `decode_token()` from `app.core.security` | Already tested, handles expiry correctly |
| Enrollment code uniqueness | Probabilistic retry without DB check | Unique DB constraint + retry loop | Race condition proof at DB level |
| Celery task dispatch from FastAPI | Direct function call, threading | `task.delay(str(id))` inside route handler body | Avoids circular import; tested pattern in orfs_job.py |
| Checkpoint score comparison | Custom operator parser | Inline Python comparison matching JSONB rule schema | Rules are simple (eq, gte, lte) — no DSL needed |
| Leaderboard ORDER BY on JSONB | Python-side sort after fetching all rows | Functional B-tree index + SQL ORDER BY | DB-level sort uses index; Python sort scans full table |

---

## Common Pitfalls

### Pitfall 1: Functional B-tree Index vs GIN for Leaderboard
**What goes wrong:** `CREATE INDEX USING GIN` on the ppa column (which Phase 1 may reference in CLAUDE.md) cannot be used for `ORDER BY`. The query planner will do a sequential scan.
**Why it happens:** GIN indexes support containment (`@>`) and existence (`?`) operators, not comparison (`<`, `>`) used by ORDER BY.
**How to avoid:** Add a migration with `CREATE INDEX idx_runs_wns_numeric ON runs (((ppa->>'worst_negative_slack')::numeric));` — this functional B-tree index supports `ORDER BY (ppa->>'worst_negative_slack')::numeric`.
**Warning signs:** `EXPLAIN ANALYZE` shows Seq Scan instead of Index Scan on the runs table for the leaderboard query.

### Pitfall 2: OpenDB Spatial Query — No Native Index
**What goes wrong:** Attempting to use a non-existent `queryRegion` or spatial index API in OpenDB Python. Official docs confirm "The data model does not support a region query."
**Why it happens:** OpenDB is a design database, not a spatial database — its primary query index is by name, not location.
**How to avoid:** Linear scan with bounding box arithmetic is the correct approach. For typical designs (hundreds to low thousands of instances in a clicked area), this is fast enough (< 100ms per query). Pre-filter by querying only within a tolerance radius.
**Warning signs:** Any code attempting `queryRegion`, R-tree, or spatial index methods will fail at runtime.

### Pitfall 3: Click-to-Inspect Coordinate System Mismatch
**What goes wrong:** PNG Y-axis is inverted relative to database coordinates. KLayout renders with Y increasing downward (image convention); OpenDB stores coordinates with Y increasing upward (EDA convention).
**Why it happens:** Different coordinate system conventions between image rendering and physical layout.
**How to avoid:** Invert Y when mapping pixel coordinates: `y_um = (1 - click_y_px / png_height) * (ymax - ymin) + ymin`. Store the bounding box from the generate_png task in the run record.
**Warning signs:** Click hits are consistently offset vertically — elements appear at reflected positions.

### Pitfall 4: Celery Circular Import in Submission Endpoint
**What goes wrong:** Importing `checkpoint_eval` at module top level in the submission route file causes a circular import (backend imports worker task, worker imports from backend).
**Why it happens:** Established in Phase 1 decisions: "Import Celery tasks inside route handler body to break circular imports."
**How to avoid:** Import `evaluate_submission` inside the route handler function body, not at the top of `submissions.py`.
**Warning signs:** `ImportError` on FastAPI startup.

### Pitfall 5: Highest-Score Retention Logic Race Condition
**What goes wrong:** Two simultaneous submissions for the same (user, assignment) pair both read the current max score and both write, resulting in either a duplicate or a lower score overwriting a higher one.
**Why it happens:** Non-atomic read-then-write pattern.
**How to avoid:** Use a database-level upsert pattern or a `SELECT ... FOR UPDATE` row lock on a unique (user_id, assignment_id) row. Alternatively, store all submissions and compute the best at read time (simpler, avoids race).
**Warning signs:** Leaderboard shows stale scores after resubmission.

### Pitfall 6: WebSocket Grade Push Channel Collision
**What goes wrong:** Publishing grade results to `logs:{run_id}` (the log streaming channel) pollutes the terminal with JSON payloads.
**Why it happens:** Reusing the log channel because it already exists.
**How to avoid:** Use a dedicated channel `grade:{run_id}` for grade results. Frontend `useGradeStream` hook subscribes to the separate WS endpoint `/api/v1/ws/runs/{run_id}/grade/stream`.
**Warning signs:** xterm.js terminal shows `{"score": 85, ...}` JSON in the log output.

### Pitfall 7: Assignment `locked_params` JSONB Schema Type Mismatch
**What goes wrong:** Locked params stored as integers in JSONB but compared as strings during submission validation, causing valid submissions to be rejected.
**Why it happens:** JSONB can store numeric types, but config.mk values are always strings.
**How to avoid:** Always cast both sides to `str` during comparison: `str(actual) != str(required_value)`. Store locked_params values as strings in JSONB from the start.
**Warning signs:** "CLOCK_PERIOD must be 10 — your run used 10" error when both values are logically identical.

---

## Code Examples

Verified patterns from the Phase 1 codebase:

### Celery Task Dispatch (inside route handler body)
```python
# Source: established pattern from backend/app/api/routes/jobs.py (Phase 1)
# Import INSIDE handler body — avoid circular import
async def submit_for_grading(...):
    ...
    from tasks.checkpoint_eval import evaluate_submission  # local import
    evaluate_submission.delay(str(submission.id))
```

### Redis Pubsub Grade Push (from checkpoint_eval task)
```python
# Source: worker/tasks/orfs_job.py publish_line() pattern
r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
result_json = json.dumps({"score": score, "checkpoint_results": checkpoint_results})
r.publish(f"grade:{run_id}", result_json.encode("utf-8"))
```

### Frontend WebSocket Hook Pattern (from useLogStream.ts)
```typescript
// Source: frontend/src/hooks/useLogStream.ts — mirror this pattern for useGradeStream.ts
// WS URL: /api/v1/ws/runs/{runId}/grade/stream?token={accessToken}
// On message: parse JSON, dispatch to courseSlice for grade display
```

### Zustand Slice Pattern (from authSlice.ts / jobSlice.ts)
```typescript
// Source: frontend/src/store/authSlice.ts
// Add courseSlice.ts following same StateCreator<StoreState> pattern
// State: courses[], activeAssignment, submissions{}
```

### SQLAlchemy async select with JOIN
```python
# Source: backend/app/api/routes/projects.py select pattern
stmt = (
    select(Course)
    .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
    .where(CourseEnrollment.user_id == user.id)
)
result = await db.execute(stmt)
courses = result.scalars().all()
```

### Monaco Editor Form/Raw Toggle
```typescript
// Source: @monaco-editor/react (monaco-react.surenatoyan.com)
import Editor from "@monaco-editor/react";

<Editor
  height="400px"
  defaultLanguage="makefile"
  value={rawContent}
  onChange={(v) => setRawContent(v ?? "")}
  theme="vs-dark"
  options={{ minimap: { enabled: false }, readOnly: false }}
/>
// Form mode: hide <Editor />, show <ParamForm /> instead
// Toggle: controlled by `mode: "form" | "raw"` state
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GIN index for all JSONB queries | Functional B-tree for ORDER BY, GIN for containment | Always been this way | Must create separate index types for different query patterns |
| opendbpy standalone pip | Run openroad -python as subprocess or inside container | N/A — never pip-installable | Click-to-inspect requires subprocess coordination |
| Polling for grade results | WebSocket push via Redis pubsub | Phase 1 established pattern | Reuse existing infrastructure |
| Separate WebSocket connections per feature | Single pubsub pattern with per-feature channels | Phase 1 established | Each new push feature needs its own Redis channel and WS endpoint |

---

## Open Questions

1. **ODB file location for click-to-inspect**
   - What we know: ODB files are stored in MinIO at `artifact_path` for each run. The query endpoint needs to access the ODB file.
   - What's unclear: Should the query task download the ODB from MinIO to a temp dir and run openroad subprocess, or mount the MinIO bucket directly? Downloading is safer (no MinIO path exposure to subprocess). Need to decide which stage ODB to query (latest completed stage).
   - Recommendation: Download the highest-stage ODB from MinIO to a temp directory, run subprocess, clean up. Add a `latest_odb_path` field to the run artifact metadata.

2. **Layout bounding box storage for coordinate mapping**
   - What we know: The click-to-inspect coordinate conversion requires the design bounding box in microns. The generate_png task runs KLayout and has access to the design extent.
   - What's unclear: The bounding box is not currently stored. The `ppa` column does not include `die_area` coordinates (only `floorplan__design__die__area` as a scalar area value).
   - Recommendation: Store `layout_bbox` as `{xmin, ymin, xmax, ymax}` in microns in the `ppa` JSONB column or as a separate field in the run's artifact metadata. Add this to `generate_png` task output.

3. **Checkpoint evaluation triggering**
   - What we know: The submission endpoint dispatches `evaluate_submission.delay()`. The grading result must include `is_submitted = True` on the run.
   - What's unclear: If grading fails (Celery task exception), should the submission remain in "grading pending" state indefinitely?
   - Recommendation: Add a `grading_status` field to submissions (`pending | complete | failed`). Set `failed` if task throws after max retries. Frontend can show "Grading failed — contact instructor" in that case.

4. **CSV export format for instructor dashboard**
   - What we know: User constraint says Claude has discretion on format details.
   - What's unclear: Whether to include checkpoint breakdown columns or just total score.
   - Recommendation: Include columns: student_display_name, submission_date, score, per-criterion result (pass/fail + points). Use Python's stdlib `csv` module in a streaming FastAPI response.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (same as Phase 1) |
| Config file | backend/tests/conftest.py (existing, extend with new fixtures) |
| Quick run command | `cd backend && python -m pytest tests/test_courses.py tests/test_assignments.py tests/test_submissions.py tests/test_checkpoint_eval.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COUR-02 | Enrollment code is VLSI-YYYY-XXXX format, unique | unit | `pytest tests/test_courses.py::test_enrollment_code_format -x` | Wave 0 |
| COUR-03 | Enrolling with valid code adds student to course | integration | `pytest tests/test_courses.py::test_enroll_success -x` | Wave 0 |
| COUR-03 | Enrolling with invalid code returns 404 | integration | `pytest tests/test_courses.py::test_enroll_invalid_code -x` | Wave 0 |
| COUR-01 | Assignment created with locked/editable params and checkpoint rules stored in JSONB | integration | `pytest tests/test_assignments.py::test_create_assignment -x` | Wave 0 |
| COUR-04 | Submission with mismatched locked param rejected with 422 | integration | `pytest tests/test_submissions.py::test_locked_param_mismatch -x` | Wave 0 |
| COUR-04 | Highest score retained across multiple submissions | integration | `pytest tests/test_submissions.py::test_highest_score_retention -x` | Wave 0 |
| COUR-05 | Hard gate failure → score = 0 regardless of scored criteria | unit | `pytest tests/test_checkpoint_eval.py::test_hard_gate_blocks_score -x` | Wave 0 |
| COUR-05 | Partial credit threshold applied correctly | unit | `pytest tests/test_checkpoint_eval.py::test_partial_credit -x` | Wave 0 |
| COUR-05 | Grade published to Redis grade:{run_id} channel after eval | unit (mocked Redis) | `pytest tests/test_checkpoint_eval.py::test_grade_published -x` | Wave 0 |
| EDIT-01 | Locked params marked read-only in form response | unit | `pytest tests/test_assignments.py::test_locked_params_in_response -x` | Wave 0 |
| LAYT-02 | Click-to-inspect returns instance name, master, nets for valid coordinate | integration (mocked subprocess) | `pytest tests/test_query.py::test_click_to_inspect_hit -x` | Wave 0 |
| LAYT-02 | Click-to-inspect returns empty list for coordinate with no element | integration (mocked subprocess) | `pytest tests/test_query.py::test_click_to_inspect_miss -x` | Wave 0 |
| DASH-01 | Leaderboard returns results ordered by score desc, WNS tiebreak, anonymized | integration | `pytest tests/test_submissions.py::test_leaderboard_order -x` | Wave 0 |
| DASH-01 | Own entry returns user_id, other entries anonymized | integration | `pytest tests/test_submissions.py::test_leaderboard_anonymity -x` | Wave 0 |
| DASH-03 | Instructor dashboard rejects student role with 403 | integration | `pytest tests/test_courses.py::test_dashboard_role_gate -x` | Wave 0 |

Frontend tests (Vitest):
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDIT-01/02 | Form/raw toggle switches component, locked params show badge | unit | `cd frontend && npx vitest run src/components/ConfigEditor` | Wave 0 |
| DASH-02 | Run comparison highlights better/worse values correctly | unit | `cd frontend && npx vitest run src/components/RunComparison` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_courses.py tests/test_assignments.py tests/test_submissions.py tests/test_checkpoint_eval.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -q && cd ../frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_courses.py` — covers COUR-01, COUR-02, COUR-03, DASH-03
- [ ] `backend/tests/test_assignments.py` — covers COUR-01, EDIT-01
- [ ] `backend/tests/test_submissions.py` — covers COUR-04, DASH-01
- [ ] `backend/tests/test_checkpoint_eval.py` — covers COUR-05
- [ ] `backend/tests/test_query.py` — covers LAYT-02 (subprocess mocked)
- [ ] `frontend/src/components/ConfigEditor/ConfigEditor.test.tsx` — covers EDIT-01, EDIT-02
- [ ] `frontend/src/components/RunComparison/RunComparison.test.tsx` — covers DASH-02
- [ ] Alembic migration `0003_courses_assignments_submissions.py` — required before any test involving new tables
- [ ] New ORM models registered in `backend/app/models/__init__.py`

---

## Sources

### Primary (HIGH confidence)
- Phase 1 codebase (read directly) — established patterns for routes, Celery tasks, Redis pubsub, Zustand slices, SQLAlchemy models
- `/opt/developments/chipatelier/CLAUDE.md` — locked param list, checkpoint_rules JSONB schema, enrollment code format, leaderboard index requirements
- `.planning/phases/02-learning-layer/02-CONTEXT.md` — all locked UX decisions
- OpenROAD documentation (openroad.readthedocs.io/en/latest/main/src/odb/README.html) — confirmed OpenDB spatial query limitation: "The data model does not support a region query"

### Secondary (MEDIUM confidence)
- @monaco-editor/react npm/GitHub (monaco-react.surenatoyan.com) — React Monaco editor wrapper, v4.x API
- PostgreSQL docs + Crunchy Data blog — functional B-tree index pattern for JSONB ORDER BY with ::numeric cast
- Celery docs (docs.celeryq.dev/en/latest/userguide/calling.html) — task chaining, apply_async, link parameter

### Tertiary (LOW confidence — flag for validation)
- OpenDB Python API for spatial/bounding box queries: no official code examples found. The linear scan approach is inferred from the API surface (getInsts, getBBox) confirmed via docs and community discussions. **Must be validated against actual ORFS container during implementation.**
- opendbpy method names (`odb.read_db`, `block.getInsts`, `inst.getBBox`, `inst.getITerms`) — inferred from C++ API names and community usage; require runtime verification inside the ORFS container.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are Phase 1 continuations; only @monaco-editor/react is new and well-documented
- Architecture: HIGH — all new entities follow Phase 1 patterns; route/model/schema/slice structure is directly analogous
- Checkpoint evaluation logic: HIGH — JSONB schema in CLAUDE.md is explicit; evaluation is pure Python arithmetic
- Leaderboard/JSONB indexing: HIGH — PostgreSQL functional B-tree index pattern is well-documented
- Click-to-inspect API (endpoint + coordinate mapping): MEDIUM — approach is clear but OpenDB method names require runtime verification
- OpenDB Python API spatial query: LOW — no runnable example code found in open sources; linear scan approach is logically correct but must be validated in ORFS container

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable libraries; OpenDB API details should be verified during Wave 0 of plan 02-05)
