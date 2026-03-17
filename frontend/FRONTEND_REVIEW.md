# Frontend Codebase Review

**Reviewed:** 2026-03-17
**Scope:** All 58 source files in `frontend/src/` (~2,400 lines of TypeScript/React)

---

## Overall Assessment

The frontend is well-structured, well-typed, and closely follows the CLAUDE.md architecture spec. Code quality is high for an early-stage project. The main concerns are: a critical double-path bug in the VNC API client, inconsistent styling approach (Tailwind classes vs inline styles), very low test coverage, and some missing error handling in WebSocket hooks.

---

## Architecture Alignment with CLAUDE.md

| Spec Requirement | Status | Notes |
|---|---|---|
| React + TypeScript | OK | React 18 + TS strict mode |
| Zustand state management | OK | 4 slices: auth, job, course, ai |
| Axios-based typed API client | OK | 10 API modules, all typed |
| xterm.js log terminal | OK | Scrollback 50k, auto-scroll, stage separators |
| Monaco config editor | OK | Form + raw mode toggle |
| MapLibre GL tiled layout viewer | Missing | Static PNG snapshot only (MVP per CLAUDE.md) |
| noVNC → OpenROAD GUI | OK | VNC session lifecycle API integrated |
| WebSocket log streaming | OK | Token refresh before WS connect |
| JWT + httpOnly refresh cookie | OK | Interceptor queues failed requests |

---

## Bugs Found

### BUG-1: Double `/api/v1` prefix in VNC API client (Critical)

**File:** `src/api/vnc.ts:30,41`

The `apiClient` (from `client.ts`) already has `baseURL: "/api/v1"`. But `vnc.ts` uses full paths:

```ts
// vnc.ts:30 — produces: /api/v1/api/v1/vnc/start/{runId}
apiClient.post(`/api/v1/vnc/start/${runId}`);

// vnc.ts:41 — produces: /api/v1/api/v1/vnc/{sessionId}
apiClient.delete(`/api/v1/vnc/${sessionId}`);
```

Every other API module uses relative paths (e.g., `/jobs/${runId}`). VNC calls will always 404.

**Fix:** Change to `/vnc/start/${runId}` and `/vnc/${sessionId}`.

### BUG-2: `@keyframes spin` defined in multiple components

**Files:** `StageStatusBar.tsx`, `LayoutSnapshot.tsx`

Both components inject `@keyframes spin` via inline `<style>` tags. If both are rendered simultaneously (which they are on RunDetailPage), the duplicate keyframe definitions are wasteful. Not a functional bug but indicates a missing shared CSS approach.

### BUG-3: `useGradeStream` connects even when `runId` is null-ish

**File:** `src/hooks/useGradeStream.ts`

The hook is called from `AssignmentView` with `submittedRunId` which starts as `null`. The early return in `connect()` handles this, but the `useEffect` still fires and sets up the cleanup function unnecessarily on every render where `runId` transitions.

---

## Code Quality Issues

### STYLE-1: Mixed styling approaches

The codebase uses **three different styling methods** inconsistently:
- **Inline styles** (dark theme): All components in `components/` and most pages
- **Tailwind utility classes**: `LoginPage.tsx`, `RegisterPage.tsx`, `ConfigEditor.tsx`, `ParamForm.tsx`
- **CSS import**: `@xterm/xterm/css/xterm.css` in LogTerminal

The login/register pages use a **light theme** with Tailwind classes (`bg-gray-50`, `text-gray-700`) while every other page uses a **dark theme** with inline styles (`#0d1117`, `#c9d1d9`). This will look jarring when navigating between login and the app. The Tailwind classes also won't work unless Tailwind is actually installed and configured — **which it is not** (not in package.json, no tailwind.config.js).

**Impact:** Login and Register pages render as unstyled HTML since Tailwind classes resolve to nothing. ConfigEditor and ParamForm also use Tailwind classes that won't apply.

**Recommendation:** Either install Tailwind or convert all Tailwind classes to inline styles consistent with the rest of the app.

### STYLE-2: No global CSS reset or base styles

There is no `index.css` or global stylesheet. The dark theme colors (`#0d1117` background, `#c9d1d9` text) are repeated in every page and component via inline styles. A minimal global CSS file would reduce duplication significantly.

### TYPE-1: Unsafe error type casting

Multiple files cast `catch` errors using `as` patterns:
```ts
const axiosErr = err as { response?: { status?: number } };
```

This is fragile. A typed `isAxiosError()` guard from axios would be safer.

### TYPE-2: `@types/react-router-dom` in dependencies (wrong place)

**File:** `package.json:18`

`@types/react-router-dom` is listed under `dependencies` instead of `devDependencies`. Also, with react-router-dom v7, the types may be bundled — this package may be unnecessary.

### PERF-1: `appendChatToken` creates new array on every token

**File:** `src/store/aiSlice.ts:67-76`

Each streaming token triggers `[...s.chatHistory]` spread + a new object for the last message. During fast token delivery, this creates significant GC pressure. Consider using an immer middleware or mutating in place for the streaming case.

### PERF-2: RunDetailPage polls even when tab is backgrounded

**File:** `src/pages/RunDetailPage.tsx:98-126`

The 3-second polling interval continues when the browser tab is in the background. Consider using `document.visibilityState` to pause polling when hidden.

---

## Security Review

### SEC-1: JWT token in WebSocket URL query parameter

**Files:** `src/hooks/useLogStream.ts:78`, `src/hooks/useGradeStream.ts:61`

```ts
const url = `...?token=${encodeURIComponent(token)}`;
```

The JWT appears in the URL query string, which means it may appear in:
- Browser history
- Server access logs
- Proxy logs

This is a known WebSocket limitation (browsers don't support custom headers for WS). The CLAUDE.md spec acknowledges this pattern. However, ensure server-side logging excludes query params, and that the WS token has a short TTL.

### SEC-2: `navigator.clipboard.writeText` without permission check

**File:** `src/pages/RunDetailPage.tsx:145`

The clipboard API may fail in non-HTTPS contexts or if permission is denied. The `.then()` handler assumes success. Should add a `.catch()` fallback.

### SEC-3: Chat streaming uses raw `fetch` bypassing auth interceptor

**File:** `src/api/ai.ts:103-109`

The `streamChat` function takes `accessToken` as a parameter and uses `fetch` directly instead of `apiClient`. This means:
- No automatic token refresh on 401
- Token could be stale if the stream starts after the access token expires

The function does handle 503, but a 401 during streaming would throw a generic error.

---

## Test Coverage

**Current:** 2 test files out of 58 source files (~3.4% file coverage)

| Test File | What it Tests |
|---|---|
| `ConfigEditor.test.tsx` | Form/raw toggle, locked params |
| `RunComparison.test.tsx` | Color coding, config diffs, empty state |

**Missing test coverage for critical paths:**
- Auth flow (login, register, token refresh)
- Job submission and status polling
- Log streaming WebSocket hook
- Grade streaming WebSocket hook
- AI chat streaming
- Route protection (ProtectedRoute)
- Stage progress computation in jobSlice

**Recommendation:** Prioritize testing the auth interceptor (`useTokenRefresh`), the job status polling logic, and the `computeStageProgress` function which is pure and easy to unit test.

---

## Missing Features (per CLAUDE.md Phase 1 MVP)

| Feature | Status |
|---|---|
| Static layout snapshot (PNG) | Implemented |
| VNC viewer integration | Implemented (but API URLs broken — BUG-1) |
| Flow control panel (stage status, run/cancel) | Implemented |
| Log streaming | Implemented |
| Project creation + file upload | Implemented |
| Job submission | Implemented |
| User auth (local accounts) | Implemented |

---

## Component Inventory

| Component | Lines | Quality | Notes |
|---|---|---|---|
| LogTerminal | 197 | Good | Clean xterm.js integration, auto-scroll state machine |
| ConfigEditor | 122 | Good | Form/raw toggle, Monaco integration |
| ParamForm | 78 | Good | Curated params with locked state |
| ParamMetadata | 68 | Good | 7 ORFS params with metadata |
| LayoutSnapshot | 256 | Good | PNG preview + VNC + downloads + click-to-inspect |
| InspectSidebar | 164 | Good | Clean cell instance display |
| StageStatusBar | 137 | Good | Pipeline progress indicator |
| PpaMetricCards | 188 | Good | Color-coded metric cards with AI explain |
| RunHistoryTable | 138 | Good | Clickable rows with status badges |
| RunComparison | 273 | Good | Side-by-side metrics + config diff |
| AiExplainPanel | 227 | Good | Cached explain with 503 handling |
| AiAdvisorPanel | 318 | Good | Parsed suggestion cards with fallback |
| AiChatTab | 408 | Good | Streaming chat with context summary |
| AssignmentView | 554 | Good | Full assignment workflow with leaderboard |
| CheckpointCards | 387 | Good | Preview + result modes with scoring |
| CourseNav | 132 | Good | Sidebar course list |
| InstructorDashboard | 335 | Good | Sortable student table with CSV export |

---

## Summary of Action Items

| Priority | Item | Effort |
|---|---|---|
| P0 (Critical) | Fix VNC API double-path prefix (BUG-1) | 5 min |
| P1 (High) | Fix Tailwind-dependent pages (STYLE-1) — login/register/config editor render unstyled | 1-2 hr |
| P1 (High) | Add clipboard.writeText error handling (SEC-2) | 5 min |
| P2 (Medium) | Add tests for auth flow, job polling, stage progress | 4-8 hr |
| P2 (Medium) | Extract shared CSS (global dark theme, keyframes) | 1 hr |
| P3 (Low) | Replace unsafe `as` error casts with `isAxiosError()` | 30 min |
| P3 (Low) | Move `@types/react-router-dom` to devDependencies | 5 min |
| P3 (Low) | Pause polling when tab is backgrounded (PERF-2) | 30 min |
