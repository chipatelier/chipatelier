---
phase: "01"
plan: "09"
subsystem: worker-orfs-metrics
tags: [gap-closure, orfs-invocation, metrics-keys, grt-failure, container-config]
dependency_graph:
  requires: ["01-08"]
  provides: ["correct-orfs-invocation", "reliable-stage-detection", "real-metrics-keys"]
  affects: ["job-pipeline", "metrics-storage", "leaderboard-accuracy"]
tech_stack:
  added: []
  patterns: ["glob-based-grt-failure-detection", "flow.sh-stage-pattern", "finish-primary-globalroute-fallback"]
key_files:
  created: []
  modified:
    - worker/container/manager.py
    - worker/tasks/orfs_job.py
    - backend/app/services/metrics_service.py
    - worker/config.py
    - backend/app/core/config.py
    - backend/tests/test_metrics.py
decisions:
  - "WORK_HOME=/workspace added to Make invocation — without it all ORFS output goes to read-only flow dir"
  - "PDK_ROOT removed from both configs — ORFS bundles PDKs in image; external mount fails if /data/pdks missing"
  - "read_only=False on container — OpenROAD writes temp files outside WORK_HOME; security via network=none+caps"
  - "tmpfs 2g — Yosys uses /tmp heavily during synthesis; 512m was insufficient"
  - "Stage detection via flow.sh 'Running *.tcl, stage' pattern — content-based patterns were unreliable guesses"
  - "GRT failure via glob for 5_1_grt-failed.odb — exit code 0 does not guarantee GRT success"
  - "WNS: finish__timing__setup__ws primary, globalroute__timing__setup__ws fallback — route__ prefix does not exist"
  - "DRC: detailedroute__route__drc_errors — finish__design__violations does not exist in real ORFS output"
  - "flow_complete: finish__timing__setup__ws presence check — replaces non-existent finish__design__violations"
metrics:
  duration_minutes: 15
  tasks_completed: 5
  files_modified: 6
  completed_date: "2026-03-16"
---

# Phase 01 Plan 09: ORFS Invocation + Metrics Key Gap Closure Summary

**One-liner:** Closed 7 critical ORFS gaps: WORK_HOME invocation fix, real metrics key names (globalroute__/detailedroute__), reliable stage detection via flow.sh pattern, GRT congestion failure detection, and PDK_ROOT removal.

## What Was Built

This plan closed 7 production-blocking gaps between the implementation and verified ORFS behavior documented in CLAUDE.md. All gaps would surface immediately on first real container run.

### GAP 1 — WORK_HOME missing (CRITICAL)

`run_container()` used `-C /OpenROAD-flow-scripts/flow` which changes directory into the read-only ORFS install tree. ORFS would write all output (results/logs/reports) there and crash.

Fixed: Replace `-C` with `--file=/OpenROAD-flow-scripts/flow/Makefile` and add `WORK_HOME=/workspace` so all output lands in the writable student workspace.

### GAP 2 — Wrong metrics keys

`metrics_service.py` used `route__timing__setup__ws` (non-existent) and `finish__design__violations` (non-existent) as primary metrics keys. DRC would always be 0 and flow_complete always False in production.

Fixed:
- WNS: `finish__timing__setup__ws` (primary), `globalroute__timing__setup__ws` (partial-run fallback)
- TNS: `finish__timing__setup__tns` (primary), `globalroute__timing__setup__tns` (fallback)
- DRC: `detailedroute__route__drc_errors` (the only real DRC key from detail route)
- flow_complete: `finish__timing__setup__ws is not None` (written by final_report.tcl)

### GAP 3 — Content-based stage detection

`STAGE_PATTERNS` dict used guesses like `r"(Starting|Finished)\s+synthesis"` which don't match ORFS log format. CLAUDE.md documents the reliable pattern: `flow.sh` prints `"Running <script>.tcl, stage <stage_id>"` before every stage.

Fixed: `STAGE_LINE_PATTERN = re.compile(r"Running (\S+\.tcl), stage (\S+)")` with `STAGE_ID_TO_NAME` prefix mapping for friendly UI display names.

### GAP 4 — PDK_ROOT volume mount

`run_container()` mounted `pdk_root:/pdks:ro` — ORFS does not use an external PDK directory. All platform files are bundled inside the image at `/OpenROAD-flow-scripts/flow/platforms/`. The mount would fail if `/data/pdks` doesn't exist on the host.

Fixed: PDK volume entry removed. `pdk_root` parameter removed from `run_container()`. `PDK_ROOT` setting removed from `worker/config.py` and `backend/app/core/config.py`.

### GAP 5 — GRT failure not detected

Global route can fail with congestion but exit code 0. ORFS writes `5_1_grt-failed.odb` instead of `5_1_grt.odb` in this case. Without this check, a congested routing failure would be marked "complete".

Fixed: `_check_grt_failure(workspace)` uses `glob.glob("results/*/*/base/5_1_grt-failed.odb")` — no need to know PLATFORM/DESIGN_NAME at detection time.

### GAP 6 — read_only=True + tmpfs 512m

CLAUDE.md explicitly prohibits `read_only=True`: "OpenROAD may write temp files outside WORK_HOME; security is provided by `--network none` + cgroup limits instead." Also `tmpfs 512m` was insufficient — Yosys uses `/tmp` heavily during synthesis (CLAUDE.md recommends 2g).

Fixed: `read_only` removed from `containers.run()` call. `tmpfs={"/tmp": "size=2g"}`.

### GAP 7 — target_stage never read from DB

Every job ran the same hard-coded Make target regardless of what stage the assignment required. The `target_stage` field in the `runs` table was never fetched.

Fixed: Extended DB query to fetch `target_stage` and `config`. Added `STAGE_TO_TARGET` mapping dict. Extracted `locked_params` from config snapshot and passed as `locked_args` to `run_container()`.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 09-01 | Fix run_container() | 7f65a54 | worker/container/manager.py |
| 09-02 | Fix orfs_job.py | 3842a69 | worker/tasks/orfs_job.py |
| 09-03 | Fix metrics_service.py | c2d5afe | backend/app/services/metrics_service.py |
| 09-04 | Remove PDK_ROOT from configs | c639902 | worker/config.py, backend/app/core/config.py |
| 09-05 | Update test_metrics.py | b637db3 | backend/tests/test_metrics.py |

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- `test_metrics.py`: 10/10 passed (added 4 new tests for flow_complete false, DRC from detailedroute, DRC zero default, finish priority over globalroute)
- `test_jobs.py`: 11/11 passed (no regressions)
- `test_tile_generator.py`: 5/5 passed (no regressions)
- `test_vnc.py`: 8/8 passed (no regressions)
- Total: 34/34 passed

## Self-Check: PASSED

All modified files confirmed on disk. All 5 task commits confirmed in git log. 34/34 tests passing.
