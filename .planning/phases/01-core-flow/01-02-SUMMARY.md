---
phase: 01-core-flow
plan: "02"
subsystem: auth
tags: [auth, jwt, argon2, zustand, axios, react-router, security]
dependency_graph:
  requires:
    - 01-01  # config.py Settings, User model, get_db, get_redis, test fixtures
  provides:
    - get_current_user dependency (used by all subsequent protected route plans)
    - require_role dependency factory
    - security.py (hash_password, verify_password, create_access_token, create_refresh_token, create_vnc_token, decode_token)
    - setupTokenRefreshInterceptor (frontend auth gate for all API calls)
    - useStore.setAuth / clearAuth / setAccessToken (frontend auth state)
  affects:
    - 01-03 (job API will use get_current_user)
    - 01-04 (project API will use get_current_user)
    - 01-05 (storage service updates user.storage_used_bytes — reflected in /users/me)
    - 01-06 (VNC API uses create_vnc_token from security.py)
tech_stack:
  added:
    - argon2-cffi 25.x (password hashing — argon2id)
    - PyJWT 2.10.x (JWT access/refresh/vnc tokens)
    - react-router-dom v6 (client-side routing with BrowserRouter)
  patterns:
    - httpOnly cookie for refresh token scoped to /api/v1/auth (not root — security boundary)
    - Redis denylist for logout (key: denylist:{jti}, TTL = remaining token lifetime)
    - Axios interceptor with queue pattern for concurrent 401 failures
    - Zustand slice composition pattern for store growth in plan 01-03
key_files:
  created:
    - backend/app/core/security.py
    - backend/app/schemas/auth.py
    - backend/app/api/deps.py
    - backend/app/api/routes/auth.py
    - backend/app/api/routes/users.py
    - frontend/src/api/client.ts
    - frontend/src/api/auth.ts
    - frontend/src/store/authSlice.ts
    - frontend/src/store/index.ts
    - frontend/src/hooks/useTokenRefresh.ts
    - frontend/src/pages/LoginPage.tsx
    - frontend/src/pages/RegisterPage.tsx
  modified:
    - backend/app/main.py (wired real auth + users routers)
    - backend/tests/test_auth.py (full test implementation from Wave 0 stubs)
    - backend/tests/test_users.py (full test implementation from Wave 0 stubs)
    - frontend/src/App.tsx (React Router, ProtectedRoute, session restoration)
    - frontend/src/main.tsx (fixed import path)
decisions:
  - "Cookie path set to /api/v1/auth (not /api/v1/auth/refresh) so Axios/requests sends it to both /logout and /refresh — security boundary maintained since it never reaches /jobs, /projects etc."
  - "Test helper pattern: TestClient does not forward cookies across path boundaries; tests must extract Set-Cookie header and pass cookies= kwarg explicitly on logout/refresh calls"
  - "No refresh token rotation in this plan — Phase 2 hardening item as documented in plan"
metrics:
  duration_minutes: 10
  completed_date: "2026-03-13"
  tasks_completed: 2
  tests_written: 13
  files_created: 12
  files_modified: 5
---

# Phase 1 Plan 02: Authentication System Summary

**One-liner:** Full auth stack — argon2id registration, JWT access token + httpOnly refresh cookie, Redis jti denylist logout, Axios interceptor with concurrent-request queue for transparent renewal, and login/register pages with Zustand state.

## What Was Built

Complete authentication implementation covering all AUTH-01 through AUTH-04 requirements and DASH-04 storage display:

**Backend:**
- `security.py`: Password hashing (argon2-cffi, argon2id), access/refresh/VNC JWT creation and decoding (PyJWT)
- `schemas/auth.py`: Pydantic v2 models — RegisterRequest, LoginRequest, TokenResponse, UserResponse
- `api/deps.py`: `get_current_user` FastAPI dependency and `require_role` factory — the auth gate for all subsequent plans
- `api/routes/auth.py`: Four endpoints — register (201), login (access token + httpOnly cookie), logout (Redis denylist + cookie clear), refresh (cookie → new access token)
- `api/routes/users.py`: `GET /users/me` protected by `get_current_user`, returns profile with `storage_used_bytes`

**Frontend:**
- `api/client.ts`: Axios instance with `withCredentials: true`
- `api/auth.ts`: Typed API wrappers for all auth operations
- `store/authSlice.ts`: Zustand slice (user, accessToken, setAuth, clearAuth, setAccessToken)
- `hooks/useTokenRefresh.ts`: Axios interceptors — auto-attaches Bearer token; on 401 queues concurrent failures, refreshes once, retries all queued requests
- `pages/LoginPage.tsx` + `RegisterPage.tsx`: Form pages with validation error messages
- `App.tsx`: React Router with ProtectedRoute, session restoration on page refresh

## Test Results

13/13 tests pass:

| Test | Status | Requirement |
|------|--------|-------------|
| test_register | PASS | AUTH-01 |
| test_register_duplicate_email | PASS | AUTH-01 |
| test_login_returns_jwt_and_cookie | PASS | AUTH-02 |
| test_login_wrong_password | PASS | AUTH-02 |
| test_logout_invalidates_refresh | PASS | AUTH-03 |
| test_refresh_token | PASS | AUTH-04 |
| test_refresh_without_cookie | PASS | AUTH-04 |
| test_protected_route_no_token | PASS | get_current_user |
| test_protected_route_bad_token | PASS | get_current_user |
| test_create_user | PASS | model |
| test_user_email_unique | PASS | model |
| test_user_storage_tracking | PASS | model |
| test_get_me_returns_storage | PASS | DASH-04 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cookie path changed from /api/v1/auth/refresh to /api/v1/auth**

- **Found during:** Task 1 — TDD RED/GREEN cycle, logout test
- **Issue:** Plan specified cookie path `/api/v1/auth/refresh`. The Python `requests` library (used by Starlette's TestClient) only sends a cookie to an endpoint if the request path starts with the cookie's path followed by `/`. The path `/api/v1/auth/refresh` does not match `/api/v1/auth/logout` because requests doesn't treat it as a directory prefix. In real browsers, logout would also fail to receive the cookie.
- **Fix:** Changed cookie path to `/api/v1/auth`. This still restricts the cookie to auth endpoints (never sent to `/jobs`, `/projects`, etc.) while allowing both `/logout` and `/refresh` to receive it. The security boundary is maintained.
- **Files modified:** `backend/app/api/routes/auth.py`

**2. [Rule 2 - Missing functionality] Redis dependency override in test fixtures**

- **Found during:** Task 1 — tests calling logout and refresh endpoints
- **Issue:** Tests needed to inject `mock_redis` into FastAPI's dependency system; the `conftest.py` `test_client` fixture only overrides `get_db`. Without a Redis override, tests connecting to a real Redis instance would fail or be non-deterministic.
- **Fix:** Added `app.dependency_overrides[get_redis] = override_redis` directly in the tests that exercise logout/refresh, cleaned up in finally blocks. No conftest change needed; this keeps overrides scoped to each test.
- **Files modified:** `backend/tests/test_auth.py`

**3. [Rule 1 - Bug] main.tsx import path used `.tsx` extension**

- **Found during:** Task 2 — `npm run build`
- **Issue:** Original stub had `import App from "./App.tsx"` which TypeScript rejects unless `allowImportingTsExtensions` is enabled.
- **Fix:** Changed to `import App from "./App"`. Also removed unused `React` import.
- **Files modified:** `frontend/src/main.tsx`

## Commits

| Hash | Description |
|------|-------------|
| 97b80fc | test(01-02): add failing tests for auth and user profile endpoints (TDD RED) |
| c35cdfc | feat(01-02): implement backend auth system and user profile endpoint (TDD GREEN) |
| dfcc5d4 | feat(01-02): implement frontend auth — Axios client, Zustand auth slice, token refresh interceptor, login/register pages |

## Self-Check: PASSED

All 12 created files found on disk. All 3 task commits verified in git log.
