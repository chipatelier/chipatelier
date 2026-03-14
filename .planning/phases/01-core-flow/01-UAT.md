---
status: testing
phase: 01-core-flow
source: 01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md, 01-05-SUMMARY.md, 01-06-SUMMARY.md
started: 2026-03-13T00:00:00Z
updated: 2026-03-13T00:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch with `docker compose up`. All 8 services (postgres, redis, minio, backend, orfs-worker, background-worker, frontend, nginx) boot without errors. GET http://localhost/api/v1/healthz returns 200 with a healthy response. No services restart-loop in the logs.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch with `docker compose up`. All 8 services (postgres, redis, minio, backend, orfs-worker, background-worker, frontend, nginx) boot without errors. GET http://localhost/api/v1/healthz returns 200 with a healthy response. No services restart-loop in the logs.
result: [pending]

### 2. User Registration
expected: Navigate to /register. Fill in email and password. Submit. Get a success response (no error message). You can then proceed to log in with the same credentials.
result: [pending]

### 3. User Login
expected: Navigate to /login. Enter registered credentials. Submit. You are redirected to the projects list (or dashboard). No error message. The browser receives an access token (visible in app state) and a httpOnly refresh cookie is set.
result: [pending]

### 4. Protected Route Enforcement
expected: Log out (or clear local storage). Try to navigate to /projects directly. You are redirected to the login page — the protected route blocks unauthenticated access.
result: [pending]

### 5. Automatic Token Refresh
expected: Log in. Wait for the access token to expire (or manually clear it from memory). Make any API request (e.g., load the projects page). The request succeeds transparently — the token refresh happens in the background without a visible logout or error.
result: [pending]

### 6. Storage Usage Display
expected: After logging in, the projects list page shows your current storage usage (e.g., "0 B of 5 GB used"). The number is visible on the page without needing to navigate elsewhere.
result: [pending]

### 7. Create Project
expected: On the projects page, click "New Project" (or equivalent). Enter a project name. Submit. The new project appears in the project list as a card. Navigating to the project shows an empty runs table.
result: [pending]

### 8. Upload Source Files
expected: Inside a project, upload a Verilog file and a config.mk file using the file upload interface. The upload completes without error. The UI acknowledges the files were received (no error message, success indication or file names shown).
result: [pending]

### 9. Submit Job
expected: After uploading files, click "New Run" (or submit job). The run appears in the run table with status "queued" or "starting". The Stage Status Bar becomes visible showing the flow has begun.
result: [pending]

### 10. Single-Run Constraint
expected: While a job is actively running, try to submit another run for the same project. The submit button is disabled (or if you bypass it, you get an error). Only one active run per project is allowed at a time.
result: [pending]

### 11. Live Log Streaming
expected: Navigate to the Run Detail page while a job is running. The Logs tab shows live log output streaming into the terminal in real-time. ANSI colors are rendered. Scrolling up pauses auto-scroll; a "Jump to bottom" button appears. Stage separator lines (═══) appear when ORFS transitions between stages.
result: [pending]

### 12. Stage Status Bar
expected: While a job is running, the Stage Status Bar at the top of the Run Detail page shows the current ORFS stage (synthesis / floorplan / place / CTS / route / GDS). The active stage has a spinning indicator. Completed stages are marked done. The bar is always visible regardless of which tab is active.
result: [pending]

### 13. Cancel Running Job
expected: While a job is running, click Cancel. The job status changes to "cancelled". The container is stopped. No further log lines arrive. The Stage Status Bar reflects the cancelled state.
result: [pending]

### 14. Results Tab with PPA Metrics
expected: After a job completes successfully, the Results tab auto-activates. It shows 5 PPA metric cards: WNS, TNS, DRC violations, cell area, and total power. Each card has a color indicator (green/yellow/red) based on thresholds. Values are numeric (not "--" or empty).
result: [pending]

### 15. Layout PNG Snapshot
expected: In the Results tab of a completed run, a layout PNG image is displayed showing the chip layout. The image loads without a broken-image icon. Below it are download links for GDS, DEF, and timing report.
result: [pending]

### 16. Artifact Downloads
expected: In the Results tab, click one of the artifact download links (e.g., "Download GDS" or "Download DEF"). A file download begins (the browser downloads or opens the file). The presigned URL works without requiring re-authentication.
result: [pending]

### 17. VNC Viewer Launch
expected: In the Results tab of a completed run, click the "Open in OpenROAD GUI" (or VNC) button. A new browser tab opens showing the noVNC viewer. The OpenROAD GUI loads with the DEF file pre-loaded (you can see the chip layout in the GUI). The original tab is unaffected.
result: [pending]

### 18. VNC Session Limit
expected: With MAX_VNC_SESSIONS set (default 8), if you attempt to start more VNC sessions than the limit, the request is rejected with a "session limit reached" error (HTTP 429). Existing sessions are unaffected.
result: [pending]

## Summary

total: 18
passed: 0
issues: 0
pending: 18
skipped: 0

## Gaps

[none yet]
