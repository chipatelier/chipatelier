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
| `frontend/src/api/projects.ts` | Add `deleteProject()`, `renameProject()`, `updateConfig()` |
| `backend/app/api/routes/projects.py` | Add `DELETE /projects/{id}`, `PATCH /projects/{id}` |
| `backend/app/api/routes/jobs.py` | Wire `config_overrides` from SubmitRequest into Make invocation |
| `worker/tasks/orfs_job.py` | Append override key=value pairs as Make CLI arguments |

**No schema changes required.** `runs.config` (JSONB) already exists for config snapshots. `config_overrides` is already in `SubmitRequest`. No new tables.

---

## Frontend Components

### `ProjectPage.tsx` — Tab Restructure

Three tabs replace the current flat layout:

- **Runs** (default tab): existing run history table + "New Run" button that opens `NewRunModal`
- **Files & Config**: two-panel layout — Verilog panel (left) + config.mk panel (right)
- **Settings**: project rename + danger zone

### `NewRunModal` (new component at `src/components/NewRunModal/`)

Modal triggered by the "New Run" button on the Runs tab.

Fields:
- **Target stage** dropdown: `synth` / `floorplan` / `place` / `cts` / `route` / `gds`
- **Override Parameters** (collapsible section, default collapsed):
  - `CLOCK_PERIOD` — placeholder: "from config.mk"
  - `CORE_UTILIZATION` — placeholder: "from config.mk"
  - `PLACE_DENSITY` — placeholder: "from config.mk"
  - `TNS_END_PERCENT` — placeholder: "from config.mk"
  - Empty fields are not sent to the backend (no override applied)
- **Run Notes** — optional free-text, stored in `runs.notes`
- Actions: Cancel | Submit Run

On submit: `POST /jobs/submit` with `{ project_id, target_stage, config_overrides, source_path, notes }`.

### `FileConfigTab` (new component at `src/components/FileConfigTab/`)

**Verilog panel (left):**
- Shows currently uploaded filename + version (e.g. `gcd.v · v3`)
- "Replace" button opens file picker (`.v`, `.sv` only)
- Read-only Monaco editor showing file contents (syntax: `systemverilog`)
- Upload posts to existing `POST /projects/{id}/upload`

**config.mk panel (right):**
- Full Monaco editor (editable, syntax: `makefile`)
- Loads current config.mk content on mount
- "Save" button → `PATCH /projects/{id}` with `{ config_mk: <content> }` → creates new `source_version`
- Unsaved changes indicator ("● Unsaved") in panel header
- On save success: version label updates (e.g. `v2 → v3`)

### `ProjectListPage.tsx` — Kebab Menu

Each project card gets a `⋮` icon button (top-right of card). Menu items:
- **Rename** — activates inline edit on card title; saves on Enter / blur; `PATCH /projects/{id}` with `{ name }`
- **Delete** — opens confirmation dialog:
  - Title: "Delete {project name}?"
  - Body: "This will permanently delete {N} runs and free {X} GB of storage. This cannot be undone."
  - Actions: Cancel | Delete Project (destructive red button)
  - On confirm: `DELETE /projects/{id}` → remove card from list

---

## Backend Changes

### `DELETE /projects/{id}`

```
DELETE /api/v1/projects/{id}
Auth: required (owner only)
```

- Returns **409 Conflict** if any run for this project has status in `["queued", "starting", "running"]` — message: `"Cancel the active run before deleting this project"`
- Deletes all `runs` rows for the project
- Deletes the `projects` row
- Queues a background Celery task to purge MinIO objects at `projects/{project_id}/`
- Returns **204 No Content** on success

### `PATCH /projects/{id}`

```
PATCH /api/v1/projects/{id}
Auth: required (owner only)
Body: { name?: string, config_mk?: string }
```

- **Rename** (`name` provided): updates `projects.name`; returns **409** if name already exists for this user
- **Config save** (`config_mk` provided): creates a new `source_versions` row with the config text; version number = existing count + 1
- Returns updated `ProjectResponse`

### Wire `config_overrides` in worker

In `worker/tasks/orfs_job.py`, when building the `make` command:

```python
# Append non-empty overrides as Make CLI args (highest priority — overrides config.mk)
override_args = [
    f"{key}={value}"
    for key, value in (config_overrides or {}).items()
    if value is not None and value != ""
]
# Final make invocation:
# make --file=... DESIGN_CONFIG=... WORK_HOME=... {target} {override_args...}
```

At submission time, store the merged config snapshot (config.mk values + overrides applied on top) in `runs.config` JSONB so the run history accurately reflects the parameters used.

---

## Data Flow

**Editing config and submitting a run with overrides:**

1. User edits config.mk in Files & Config tab → clicks Save
2. `PATCH /projects/{id}` → new `source_version` row created
3. User switches to Runs tab → clicks "New Run"
4. `NewRunModal` opens — user selects stage, optionally expands Override Parameters, fills CLOCK_PERIOD=8, adds note
5. User clicks Submit Run
6. `POST /jobs/submit` → `{ project_id, target_stage: "route", config_overrides: { CLOCK_PERIOD: "8" }, source_path: "projects/{id}/v3", notes: "testing tighter clock" }`
7. Worker copies files from MinIO → builds Make command with `CLOCK_PERIOD=8` appended → stores merged config in `runs.config`
8. Modal closes → Runs tab shows new run row with status "queued"

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Delete with active run | Backend 409 → confirmation dialog shows error message inline |
| Rename to duplicate name | Backend 409 → inline error under rename field |
| Config save failure | Toast error; Monaco content preserved |
| Override field (non-numeric input) | Client-side validation; submit button disabled until resolved |
| File upload wrong extension | Existing backend validation (400); toast error |

---

## Testing

### Backend (pytest)

- `DELETE /projects/{id}`: ownership check (403), 409 on active run, 204 success, MinIO purge task queued
- `PATCH /projects/{id}`: rename success, rename duplicate (409), config save creates new source_version
- `config_overrides` Make arg injection: unit test that override dict is correctly serialized to CLI args

### Frontend (Vitest)

- `NewRunModal`: renders with correct fields, submit with no overrides (empty config_overrides), submit with overrides (correct payload shape), cancel closes modal
- Delete confirmation dialog: shows project name + storage, cancel does not call API, confirm calls `deleteProject()`
- `ProjectPage` tab navigation: switching tabs renders correct content
- `FileConfigTab`: unsaved indicator appears on edit, clears after save

---

## Out of Scope

- File version history browser (view/restore previous versions) — Phase 2
- All 7 ORFS exposed params beyond the 4 listed — Phase 2 config editor
- AI config advisor button — Phase 3
- Run comparison view — Phase 2
- SSO / admin-level project management — Phase 3
