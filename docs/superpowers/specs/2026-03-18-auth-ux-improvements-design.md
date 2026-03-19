# Auth UX Improvements — Design Spec

**Date:** 2026-03-18
**Status:** Approved

---

## Problem

1. Logout button only exists on `ProjectListPage`. Users on `ProjectPage` and `RunDetailPage` have no way to sign out.
2. No password change option exists in the GUI.
3. No self-service password recovery — users who forget their password require manual DB intervention.

---

## Solution Overview

Three linked improvements:

1. **Shared `AppHeader` component** — replaces per-page inline headers across all protected pages, carrying a user dropdown with logout and change-password actions.
2. **Change Password modal** — accessible from the user dropdown on any protected page.
3. **Admin-token password reset** — admin generates a short-lived token out-of-band; user enters email + token + new password on a `/reset-password` page linked from the login screen.

---

## 1. AppHeader Component

### Component: `src/components/AppHeader/AppHeader.tsx`

**Props:**
```typescript
interface AppHeaderProps {
  breadcrumbs?: React.ReactNode; // page-specific nav, rendered center-left
  actions?: React.ReactNode;     // page-specific action buttons, rendered right of storage chip
}
```

**Layout (left → right):**
- ChipAtelier wordmark/logo (links to `/projects`)
- Breadcrumbs slot (passed by each page)
- Page-specific actions slot (e.g., "New Project" button on ProjectListPage)
- Storage usage chip (GB used / quota, moved from ProjectListPage)
- User dropdown button (shows `display_name ?? email`)

The `actions` slot lets each page inject its own header buttons (e.g., "New Project") without moving them out of the header row. The "New Project" button stays in the header on `ProjectListPage` via `actions={<NewProjectButton />}`.

**Adopted by:**
- `ProjectListPage` — remove existing inline header; pass `actions={<NewProjectButton />}`, no breadcrumbs
- `ProjectPage` — remove existing breadcrumb row; pass breadcrumb `Projects > {project.name}`, no actions
- `RunDetailPage` — remove existing breadcrumb row; pass breadcrumb `Projects > {project.name} > Run #{n}`, no actions

---

## 2. User Dropdown

A small popover anchored to the user button in `AppHeader`. State (open/closed) managed with local `useState`. Closes on outside click via a transparent overlay or `useEffect` document listener.

**Contents (top to bottom):**
1. User email — non-interactive label
2. "Change Password" — opens Change Password modal
3. Horizontal divider
4. "Sign out" — calls `logout` from `src/api/auth.ts` (imported as `authLogout` locally, following the same alias pattern used in `ProjectListPage`), clears store via `clearAuth()`, navigates to `/login`

---

## 3. Change Password Modal

### Component: `src/components/ChangePasswordModal/ChangePasswordModal.tsx`

**Props:**
```typescript
interface ChangePasswordModalProps {
  open: boolean;
  onClose: () => void;
}
```

**Fields:**
- Current password (required)
- New password (required, min 8 chars)
- Confirm new password (required, must match new password)

**Validation:**
- Client-side: confirm must match new password; new must not equal current password. Both comparisons are plaintext-to-plaintext (both values come from the request body — do not hash before comparing).
- Server error (wrong current password → 400) displayed inline below the form.
- Submit button shows "Saving..." and is disabled while the request is in flight, matching the existing LoginPage/RegisterPage loading state pattern.
- Submitting `new_password == current_password` is rejected client-side with "New password must differ from current password." The backend also enforces this.

**API call:** `POST /api/v1/auth/change-password`
```typescript
{ current_password: string; new_password: string }
```
On success: show brief success message, close modal after 1.5 s.

---

## 4. Forgot Password — Login Page

A "Forgot your password?" text link placed below the "Sign in" button on `LoginPage`. Uses React Router `<Link to="/reset-password">`.

`LoginPage` reads `useLocation().state?.flash` on mount. If a flash string is present, display a green dismissible banner above the form. Immediately after reading, clear the state from history to prevent reappearing on back-navigation:
```typescript
window.history.replaceState({}, document.title);
```
Place this call in a `useEffect` that runs once on mount, after reading the flash value.

---

## 5. Reset Password Page

### Page: `src/pages/ResetPasswordPage.tsx`

**Route:** `/reset-password` (unprotected — added to public routes in `App.tsx`)

**Fields:**
- Email address
- Reset token (8-char uppercase alphanumeric, provided by admin out-of-band)
- New password (min 8 chars)

**API call:** `POST /api/v1/auth/reset-password`
```typescript
{ email: string; token: string; new_password: string }
```

**On success:** navigate to `/login` passing React Router location state:
```typescript
navigate('/login', { state: { flash: 'Password reset successfully. Please sign in.' } });
```

**On error:** inline message "Invalid or expired token." (same message for unknown email and bad token — no email enumeration).

**Link back to login** at the bottom of the page.

---

## 6. Backend Endpoints

### `POST /api/v1/auth/change-password` (authenticated)

**Pydantic schema:**
```python
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
```

**Logic:**
1. Require valid Bearer token via `get_current_user` dependency.
2. Verify `current_password` against `users.password_hash` (argon2id). If mismatch → 400 `{ "detail": "Current password is incorrect" }`.
3. Compare `new_password` string to `current_password` string directly (both are plaintext from the request body — do not use a hash comparison here). If equal → 400 `{ "detail": "New password must differ from current password" }`.
4. Hash `new_password` with argon2id, update `users.password_hash`.
5. Return 204 No Content.

**Session invalidation:** The 15-minute access token TTL is the accepted security boundary for self-service password change (the user is authenticated and changing their own password). No active token revocation is performed.

---

### `POST /api/v1/admin/reset-token` (admin only)

**Pydantic schema:**
```python
class GenerateResetTokenRequest(BaseModel):
    email: str

class ResetTokenResponse(BaseModel):
    token: str
    expires_in_seconds: int
```

**Logic:**
1. Use `require_role("admin")` dependency (defined in `app/api/deps.py`) — this is the established pattern for admin-only endpoints.
2. Look up user by email. Return 404 if not found. **Note:** this is an intentional exception to the no-email-enumeration rule — admins are trusted actors and operate on known user lists, so revealing whether an email exists is acceptable for this endpoint only.
3. Generate an 8-character cryptographically random uppercase alphanumeric token:
   ```python
   import secrets, string
   alphabet = string.ascii_uppercase + string.digits
   token = ''.join(secrets.choice(alphabet) for _ in range(8))
   ```
   This yields ~47 bits of entropy, sufficient given the 1-hour TTL and rate limiting.
4. Store in Redis: key `pwreset:{email}`, value `{token}`, TTL 3600 s. A repeated call for the same email **overwrites** the previous token — the old token becomes invalid immediately.
5. Return `{ "token": "XXXXXXXX", "expires_in_seconds": 3600 }`.

**Security note:** This endpoint returns the token in plaintext JSON. Ensure request/response logging is not enabled at DEBUG level for this route. Admins communicate the token to the student out-of-band (verbally or via institutional email).

**Router registration:** Mount this router in `backend/app/main.py` under prefix `/api/v1/admin`, following the same pattern as existing routers (e.g., `app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])`).

---

### `POST /api/v1/auth/reset-password` (unauthenticated)

**Pydantic schema:**
```python
class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str = Field(min_length=8)
```

**Logic:**
1. Look up `pwreset:{email}` in Redis.
2. If key missing → 400 `{ "detail": "Invalid or expired reset token" }`.
3. Compare stored token to submitted token using `hmac.compare_digest(stored_token, submitted_token)` (constant-time — prevents timing side-channel). If mismatch → 400 same generic error.
4. Look up user by email. If not found → 400 same generic error (no email enumeration).
5. Hash `new_password`, update `users.password_hash`.
6. Delete Redis key immediately after successful password update (single-use — replay rejected).
7. Return 204 No Content.

**Session invalidation after reset:** The 15-minute access token TTL is the accepted security boundary. Active refresh tokens are not explicitly revoked — an attacker with a valid refresh token can obtain one more access token before their session expires. This risk is accepted given the on-premise university context and the 15-minute window.

**Rate limiting:** Implement as a reusable `rate_limit` dependency in `app/api/deps.py`:

```python
async def rate_limit(request: Request, redis=Depends(get_redis)) -> None:
    # Read real IP from X-Forwarded-For (first entry = client IP, set by Nginx)
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host or "unknown")
    key = f"ratelimit:reset:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 600)  # 10-minute window, set on first increment
    if count > 10:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
```

Apply to the `reset-password` endpoint via `Depends(rate_limit)`. This uses INCR + EXPIRE (fixed window, not sliding) which is sufficient for this use case. Add a comment in the code noting the Nginx proxy topology so future developers understand why `X-Forwarded-For` is trusted.

---

## 7. `storage_quota_bytes` on UserResponse

The frontend `UserResponse` type already includes `storage_quota_bytes: number | null` but the backend schema is missing it.

**Interim implementation:** The `Institution` ORM model and `institution_id` foreign key on `User` do not exist yet (they are part of a future phase). Return `null` unconditionally for `storage_quota_bytes` until that model is built. The frontend already handles `null` gracefully (shows no quota limit).

**Backend changes:**
- `schemas/auth.py` `UserResponse`: add `storage_quota_bytes: int | None = None`
- `routes/users.py` `/users/me`: construct the response explicitly so Pydantic does not fail trying to auto-map a missing ORM attribute:

```python
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        storage_used_bytes=current_user.storage_used_bytes,
        storage_quota_bytes=None,  # populated when Institution model is added
        created_at=current_user.created_at,
    )
```

No Alembic migration is needed.

---

## 8. Frontend API Changes

**`src/api/auth.ts` — add:**
```typescript
changePassword(current_password: string, new_password: string): Promise<void>
// POST /auth/change-password — authenticated

resetPassword(email: string, token: string, new_password: string): Promise<void>
// POST /auth/reset-password — unauthenticated
```

**`src/api/admin.ts` — new file:**
```typescript
generateResetToken(email: string): Promise<{ token: string; expires_in_seconds: number }>
// POST /admin/reset-token — admin authenticated
```

---

## 9. New Files

| File | Purpose |
|------|---------|
| `frontend/src/components/AppHeader/AppHeader.tsx` | Shared protected-page header |
| `frontend/src/components/ChangePasswordModal/ChangePasswordModal.tsx` | Change password dialog |
| `frontend/src/pages/ResetPasswordPage.tsx` | Admin-token reset flow |
| `frontend/src/api/admin.ts` | Admin API client (reset token generation) |
| `backend/app/api/routes/admin.py` | Admin endpoints (reset token generation) |

---

## 10. Modified Files

| File | Change |
|------|--------|
| `frontend/src/pages/ProjectListPage.tsx` | Adopt AppHeader with `actions` slot, remove inline header |
| `frontend/src/pages/ProjectPage.tsx` | Adopt AppHeader with breadcrumb |
| `frontend/src/pages/RunDetailPage.tsx` | Adopt AppHeader with breadcrumb |
| `frontend/src/pages/LoginPage.tsx` | Add "Forgot your password?" link + flash message display + history clear |
| `frontend/src/App.tsx` | Add `/reset-password` public route |
| `frontend/src/api/auth.ts` | Add `changePassword`, `resetPassword` |
| `backend/app/api/routes/auth.py` | Add `change-password`, `reset-password` endpoints |
| `backend/app/api/routes/users.py` | Populate `storage_quota_bytes` via institution join in `/users/me` |
| `backend/app/main.py` | Register admin router under `/api/v1/admin` |
| `backend/app/schemas/auth.py` | Add `storage_quota_bytes: int | None` to `UserResponse` |

---

## 11. Security Notes

- Reset tokens are single-use and 1-hour TTL — replayed tokens are rejected.
- Token comparison uses `hmac.compare_digest` — no timing side-channel.
- Token errors never reveal whether an email is registered (public endpoints only; admin endpoint intentionally returns 404 for unknown email).
- Change password requires the current password — prevents session hijack escalation.
- New password must differ from current password — enforced client-side and server-side.
- Concurrent admin token generation for the same email silently overwrites the previous token.
- No SMTP dependency — admin communicates token out-of-band.
- Rate limiting (10 req / 10 min / IP) protects the reset endpoint against automated guessing. Requires correct proxy header configuration behind Nginx.
- The 15-minute access token TTL is the accepted security boundary for both change-password and reset-password — no active token revocation is performed.
