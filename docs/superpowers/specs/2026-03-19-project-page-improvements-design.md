# Project Page Improvements — Design Spec

**Date:** 2026-03-19
**Status:** Approved
**Scope:** ProjectPage restructure, file management, ORFS config customization, project deletion

---

## Problem Statement

The current ProjectPage has three UX gaps:

1. **No project deletion** — once created, projects cannot be deleted or renamed from any UI surface
2. **Bundled file upload** — Verilog and config.mk must be uploaded together; no way to replace one independently or edit config inline
3. **No ORFS parameter exposure** — `config_overrides` exists in the backend schema but is never surfaced to students; all ORFS tuning requires editing and re-uploading config.mk

---

## Decisions Summary

| Topic | Decision |
|---|---|
| Layout | Tabs: Runs \| Files & Config \| Settings |
| File management | Verilog: upload-only + read-only Monaco preview; config.mk: full Monaco inline editor |
| ORFS params | config.mk as baseline + per-run overrides at submission time |
| Delete behavior | Confirmation dialog showing storage impact → hard delete |
| New Run flow | Modal with stage, collapsible override params, run notes |
| Project card actions | Kebab menu with Rename + Delete |
| Implementation scope | Option B — full redesign as designed, no Phase 2 scope creep |

---

## Architecture Overview

### What Changes

| Layer | Change |
|---|---|
| `frontend/src/pages/ProjectPage.tsx` | Restructured into 3 tabs: Runs, Files & Config, Settings |
| `frontend/src/pages/ProjectListPage.tsx` | Kebab menu per card with Rename + Delete |
| `frontend/src/components/NewRunModal/` | New component — modal for run submission |
| `frontend/src/components/FileConfigTab/` | New component — Verilog upload + config.mk Monaco editor |
| `frontend/src/api/projects.ts` | Add `deleteProject()`, `renameProject()`, `updateProject()`, `getProjectSource()`, `getProjectConfig()`; `POST /projects/{id}/upload` already exists — no change |
| `backend/app/api/routes/projects.py` | Add `DELETE /projects/{id}`, `PATCH /projects/{id}`, `GET /projects/{id}/source`, `GET /projects/{id}/config` |
| `backend/app/schemas/projects.py` | Add `config_version`, `verilog_version` to `ProjectResponse` |
| `backend/app/schemas/jobs.py` | Add `notes: str \| None = None` to `SubmitRequest` |
| `backend/app/api/routes/jobs.py` | Wire `notes` into `Run` creation; store config snapshot correctly |
| `worker/tasks/orfs_job.py` | Extract both `locked_params` and `config_overrides` from `runs.config`; `locked_params` appended last |

**No new database tables.** `runs.config` JSONB already exists. `config_overrides` is already in `SubmitRequest`. `ProjectResponse` already includes `storage_bytes: int` and `run_count: int` — no change needed for the delete dialog.

---

## Schema Changes

### `ProjectResponse`

Add three new fields:
```python
class ProjectResponse(BaseModel):
    id: UUID
    name: str
    pdk: str
    storage_bytes: int            # existing
    created_at: datetime          # existing
    run_count: int                # existing
    config_version: int = 0      # new — increments on each config.mk save
    verilog_version: int = 0     # new — increments on each Verilog upload
    latest_source_path: str | None = None  # new — backend-computed MinIO prefix; frontend passes this as source_path on submit
```

`latest_source_path` is computed by the backend on every project fetch. For projects using the new upload path convention it is `projects/{id}/verilog/v{verilog_version}`. For projects created before this change (legacy path), it is `projects/{id}/v{legacy_N}` where `legacy_N` is the version number stored at upload time (see Alembic migration). The **frontend never constructs `source_path` manually** — it reads `latest_source_path` directly from `ProjectResponse`.

### Alembic Migration

```python
op.add_column('projects', sa.Column('config_version', sa.Integer(), nullable=False, server_default='0'))
op.add_column('projects', sa.Column('verilog_version', sa.Integer(), nullable=False, server_default='0'))
op.add_column('projects', sa.Column('latest_source_path', sa.String(), nullable=True))
```

For existing projects, `latest_source_path` starts NULL. On first access of `GET /projects/{id}` the backend backfills it by checking MinIO for the highest `v{N}/` prefix under `projects/{id}/`. This is a lazy backfill — no data migration script needed.

---

## MinIO Path Conventions

All project MinIO objects live under the prefix `projects/{project_id}/` — a single prefix purge on delete covers source files. Run output artifacts are stored separately (see Delete section).

| Content | MinIO path |
|---|---|
| Verilog source (new) | `projects/{id}/verilog/v{N}/` (one or more `.v`/`.sv` files) |
| Verilog source (legacy) | `projects/{id}/v{N}/` (existing projects — N is stored in `latest_source_path`) |
| config.mk | `projects/{id}/config/v{N}/config.mk` |

**No data migration needed.** Legacy upload paths stay in MinIO as-is. `latest_source_path` on `ProjectResponse` always points to the correct current path (new or legacy). `GET /projects/{id}/source` reads whichever path `latest_source_path` points to.

`source_path` in `SubmitRequest` is the Verilog source prefix. The worker copies all files under that prefix into the job workspace. The **frontend always passes `project.latest_source_path` as `source_path`** — it never constructs this value itself.

---

## Frontend Components

### `ProjectPage.tsx` — Tab Restructure

Three tabs replace the current flat layout:

- **Runs** (default tab): existing run history table + "New Run" button
- **Files & Config**: two-panel layout — Verilog panel (left) + config.mk panel (right)
- **Settings**: project rename + danger zone

### `NewRunModal` (new component at `src/components/NewRunModal/`)

Modal triggered by the "New Run" button on the Runs tab.

**Pre-submit guards** (enforced before the modal opens — show tooltip explaining why):
- `verilog_version === 0`: "Upload a Verilog file before submitting a run"
- `config_version === 0`: "Save a config.mk before submitting a run"
- Active run in progress: existing "Cancel active run" guard

Fields:
- **Target stage** dropdown: `synth` / `floorplan` / `place` / `cts` / `route` / `finish` (displayed as "GDS (Full Flow)" for `finish`)
- **Override Parameters** (collapsible section, default collapsed):

  | Field | Type | Valid range |
  |---|---|---|
  | `CLOCK_PERIOD` | float | > 0 |
  | `CORE_UTILIZATION` | integer | 1–99 |
  | `PLACE_DENSITY` | float | 0.01–0.99 |
  | `TNS_END_PERCENT` | integer | 0–100 |

  Empty fields are omitted from `config_overrides`. Submit button disabled if any filled field fails range validation.

- **Run Notes** — optional free-text
- Actions: Cancel | Submit Run

On submit: `POST /jobs/submit` with `{ project_id, target_stage, config_overrides, source_path, notes }`.
- `source_path` = `project.latest_source_path` from `ProjectResponse` — the frontend never constructs this itself
- `config_overrides` omits empty fields; if all empty, omit the key entirely

### `FileConfigTab` (new component at `src/components/FileConfigTab/`)

**Verilog panel (left):**
- Shows version label from `projects.verilog_version` (e.g. `v3`). When multiple files exist, `filename` from `GET /source` is displayed as e.g. `gcd.v (2 files)`; when one file, the exact filename.
- "Upload" / "Replace" button opens file picker (`.v`, `.sv` only) → `POST /projects/{id}/upload` (existing endpoint); on success, refetch `ProjectResponse` to update `verilog_version` label
- Read-only Monaco editor shows content from `GET /projects/{id}/source` (syntax: `systemverilog`); shows "No Verilog uploaded yet" empty state on 404

**config.mk panel (right):**
- Full Monaco editor (editable, syntax: `makefile`)
- Loads content on mount from `GET /projects/{id}/config`; starts blank (version 0) for new projects
- "Save" button → `PATCH /projects/{id}` with `{ config_mk: <content> }` → refetch `ProjectResponse` to update `config_version` label
- Unsaved changes indicator ("● Unsaved") in panel header; cleared after successful save

### `ProjectListPage.tsx` — Kebab Menu

Each project card gets a `⋮` icon button (top-right of card). Menu items:
- **Rename** — activates inline edit on card title; saves on Enter / blur; `PATCH /projects/{id}` with `{ name }`
- **Delete** — opens confirmation dialog:
  - Title: "Delete {project name}?"
  - Body: "This will permanently delete {N} runs and free {X} GB of storage. This cannot be undone."
  - Storage: `(storage_bytes / 1e9).toFixed(1) + " GB"` (from `ProjectResponse.storage_bytes`)
  - If backend returns 409 (active run): show error inline in dialog
  - On 204: remove card from list

---

## Backend Changes

### `backend/app/schemas/jobs.py` — Add `notes` to `SubmitRequest`

```python
class SubmitRequest(BaseModel):
    project_id: UUID
    target_stage: TargetStage = TargetStage.finish
    config_overrides: dict[str, str] | None = None   # all values are strings — Make args are always strings
    source_path: str | None = None
    notes: str | None = None          # ← add this field
```

`config_overrides` values are `str` throughout — this is correct because Make CLI args are always strings (`CLOCK_PERIOD=8`). Range validation (e.g. `PLACE_DENSITY` 0.01–0.99) is **client-side only**. The backend passes values through to Make without type-checking; ORFS will fail at runtime with a clear error if a value is invalid.

In `jobs.py` submit handler, add backend guards before creating the `Run`:
```python
# Backend pre-submit validation (guards frontend cannot bypass):
if project.latest_source_path is None:
    raise HTTPException(400, "Upload a Verilog file before submitting a run")
if project.config_version == 0:
    raise HTTPException(400, "Save a config.mk before submitting a run")
```

Then wire notes:
```python
run = Run(..., config=config_snapshot, notes=body.notes)
```

### New read endpoints in `projects.py`

```
GET /api/v1/projects/{id}/source
Auth: required (owner only)
Returns: { filename: str, content: str, version: int }
```
Fetches the latest Verilog from MinIO at the path stored in `projects.latest_source_path`. If multiple `.v`/`.sv` files exist, concatenates them in alphabetical order and sets `filename` to e.g. `"gcd.v (2 files)"`. This concatenated response is **display-only** — it is not used for job submission (the worker uses the MinIO prefix directly). Returns 404 when `latest_source_path` is NULL (no upload yet).

```
GET /api/v1/projects/{id}/config
Auth: required (owner only)
Returns: { content: str, version: int }
```
Fetches `projects/{id}/config/v{config_version}/config.mk`. Returns `{ content: "", version: 0 }` when `config_version === 0` (no save yet — the Monaco editor starts blank).

### `DELETE /projects/{id}`

```
DELETE /api/v1/projects/{id}
Auth: required (owner only)
```

- Returns **409 Conflict** if any run has status in `["queued", "starting", "running"]`
- Deletes all `runs` rows and the `projects` row from PostgreSQL
- Queues a background Celery task (max_retries=3, exponential backoff) that:
  1. Purges all MinIO objects under prefix `projects/{project_id}/` (source files and config saves)
  2. Purges run output artifacts: enumerates `runs.artifact_path` for all runs of this project and deletes each artifact path from MinIO
- Purge is best-effort — if the Celery task exhausts retries, the orphaned artifacts are acknowledged tech debt (no automatic recovery in Phase 1)
- Returns **204 No Content** immediately (purge happens asynchronously)

### `PATCH /projects/{id}`

```
PATCH /api/v1/projects/{id}
Auth: required (owner only)
Body: { name?: string, config_mk?: string }
```

Both fields may be sent in the same request and are processed together atomically. If both are present: rename AND save config.mk in a single transaction.

- **Rename** (`name` provided): updates `projects.name`; returns **409** if name already exists for this user
- **Config save** (`config_mk` provided): writes to MinIO at `projects/{id}/config/v{config_version+1}/config.mk` **first**; only increments `projects.config_version` in the DB after the MinIO write succeeds. If the MinIO write fails, the DB is not updated and the endpoint returns 500.
- Returns updated `ProjectResponse`

### `runs.config` JSONB Structure and Make Arg Wiring

This spec extends `runs.config` to store student overrides under a separate key alongside the existing `locked_params`:

```python
# In jobs.py submit handler:
config_snapshot = {
    "locked_params": assignment.locked_params if assignment else {},
    "config_overrides": body.config_overrides or {},
}
run = Run(..., config=config_snapshot, notes=body.notes)
```

**In `orfs_job.py` — student overrides first, locked_params last (instructor always wins via Make last-arg semantics):**
```python
config_snapshot = (row.config if row else None) or {}
locked_params = config_snapshot.get("locked_params", {})
config_overrides = config_snapshot.get("config_overrides", {})

make_override_args = (
    [f"{k}={v}" for k, v in config_overrides.items() if v is not None and v != ""] +
    [f"{k}={v}" for k, v in locked_params.items()]
)
# make --file=... DESIGN_CONFIG=... WORK_HOME=... {target} {make_override_args...}
```

`runs.config` stores the override keys only — no full config.mk text. The run history UI labels `config_overrides` as "Parameter overrides."

---

## Data Flow

**Editing config and submitting a run with overrides:**

1. User opens Files & Config tab → panels fetch `GET /projects/{id}/source` and `GET /projects/{id}/config`
2. User edits config.mk → clicks Save → `PATCH /projects/{id}` → MinIO write; `config_version` incremented
3. User switches to Runs tab → clicks "New Run" (button enabled: `verilog_version > 0` and `config_version > 0`)
4. `NewRunModal` opens → user selects `route`, fills `CLOCK_PERIOD=8`, adds note
5. Frontend sets `source_path = project.latest_source_path` from `ProjectResponse`
6. `POST /jobs/submit` → `{ project_id, target_stage: "route", config_overrides: { "CLOCK_PERIOD": "8" }, source_path: "projects/{id}/verilog/v3", notes: "..." }`
7. Backend creates `Run` with `config = { "locked_params": {}, "config_overrides": { "CLOCK_PERIOD": "8" } }`, `notes` populated
8. Worker builds Make command: `make ... route CLOCK_PERIOD=8`
9. Modal closes → Runs tab shows new run row with status "queued"

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Delete with active run | Backend 409 → error shown inline in confirmation dialog |
| Rename to duplicate name | Backend 409 → inline error under rename field |
| Config save failure | Toast error; Monaco content preserved (unsaved indicator remains) |
| Override field out of range | Client-side validation; Submit button disabled |
| File upload wrong extension | Existing backend 400; toast error |
| `GET /source` — no upload | 404 → Verilog panel shows "No Verilog uploaded yet" empty state |
| `GET /config` — no save | Returns `{ content: "", version: 0 }` → Monaco starts blank |
| Submit with no Verilog uploaded | Frontend disables "New Run" button; backend returns 400 as second line of defense |
| Submit with no config.mk saved | Frontend disables "New Run" button; backend returns 400 as second line of defense |
| `PATCH` with both `name` and `config_mk` | Processed together atomically — both applied |
| Config save MinIO failure | 500 returned; DB not updated; Monaco content preserved |

---

## Testing

### Backend (pytest)

- `DELETE /projects/{id}`: ownership 403, 409 on active run, 204 success, purge task queued (source prefix + run artifact paths)
- `PATCH /projects/{id}` rename: success, duplicate 409
- `PATCH /projects/{id}` config save: MinIO write at correct path, `config_version` incremented
- `PATCH /projects/{id}` both fields: both name and config applied atomically
- `GET /projects/{id}/source`: content returned, fallback to legacy path, 404 when `verilog_version === 0`
- `GET /projects/{id}/config`: content returned, empty string when `config_version === 0`
- `SubmitRequest` with `notes`: `run.notes` populated
- `config_overrides` Make args: `config_overrides` entries appear before `locked_params` entries in `make_override_args`
- Upload handler: `verilog_version` incremented, path uses new `verilog/v{N}/` convention

### Frontend (Vitest)

- `NewRunModal`: Submit disabled when `verilog_version === 0`; disabled when `config_version === 0`; overrides with out-of-range values disable Submit; empty overrides omit `config_overrides` from payload; `source_path` set from `project.latest_source_path`; `finish` stage shows "GDS (Full Flow)" label
- Delete dialog: storage shown in GB, cancel does not call API, 409 shows inline error, 204 removes card
- `ProjectPage` tab navigation: default is Runs, switching renders correct content
- `FileConfigTab`: fetches source and config on mount; shows empty state for 404 source; unsaved indicator appears on edit, clears after save

---

## Out of Scope

- File version history browser (view/restore previous Verilog versions) — Phase 2
- Exposing more than the 4 ORFS params in the override panel — Phase 2 config editor
- Full config.mk parse + merged snapshot in `runs.config` — Phase 2
- AI config advisor button — Phase 3
- Run comparison view — Phase 2
- SSO / admin-level project management — Phase 3
