# Auth UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared AppHeader with user dropdown (logout + change password) to all protected pages, plus admin-token-based password reset accessible from the login page.

**Architecture:** Backend gains three new endpoints (`change-password`, `reset-password`, `admin/reset-token`) plus a `rate_limit` dependency. The frontend gains a shared `AppHeader` component adopted by all three protected pages, a `ChangePasswordModal`, and a `ResetPasswordPage`.

**Tech Stack:** FastAPI, SQLAlchemy async, Redis (fakeredis in tests), argon2id, React 18, TypeScript, Zustand, `@testing-library/react`, Vitest, pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-03-18-auth-ux-improvements-design.md`

---

## Chunk 1: Backend

### Task 1: Add `storage_quota_bytes` to `UserResponse` and update `/users/me`

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/routes/users.py`
- Test: `backend/tests/test_users.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_users.py`:

```python
def test_get_me_returns_storage_quota_bytes(test_client):
    """GET /users/me must include storage_quota_bytes field (None when no institution)."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "quota_user@example.com", "password": "securepass1"},
    )
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": "quota_user@example.com", "password": "securepass1"},
    )
    token = login_resp.json()["access_token"]

    resp = test_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "storage_quota_bytes" in data
    assert data["storage_quota_bytes"] is None  # no institution yet
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_users.py::test_get_me_returns_storage_quota_bytes -v
```

Expected: FAIL — `storage_quota_bytes` not in response.

- [ ] **Step 3: Add field to `UserResponse` schema**

In `backend/app/schemas/auth.py`, add after `storage_used_bytes`:

```python
storage_quota_bytes: int | None = None
```

- [ ] **Step 4: Update `/users/me` to construct response explicitly**

Replace `backend/app/api/routes/users.py` entirely:

```python
"""User profile endpoints."""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile.

    storage_quota_bytes is None until the Institution model is implemented.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        storage_used_bytes=current_user.storage_used_bytes,
        storage_quota_bytes=None,
        created_at=current_user.created_at,
    )
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_users.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/routes/users.py backend/tests/test_users.py
git commit -m "feat: add storage_quota_bytes to UserResponse (null until Institution model)"
```

---

### Task 2: Add `rate_limit` dependency to `deps.py`

**Files:**
- Modify: `backend/app/api/deps.py`

This is a utility used by the reset-password endpoint. No isolated test — it is covered by the reset-password tests in Task 4.

- [ ] **Step 1: Add `rate_limit` to `backend/app/api/deps.py`**

Append after the `require_role` function:

```python
from fastapi import Request
from app.core.redis import get_redis


async def rate_limit(request: Request, redis=Depends(get_redis)) -> None:
    """Allow at most 10 requests per IP per 10 minutes.

    Reads real client IP from X-Forwarded-For set by Nginx.
    Uses INCR + EXPIRE (fixed window) — sufficient for password reset.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host or "unknown")
    key = f"ratelimit:reset:{ip}"
    count = await redis.incr(key)
    if count == 1:
        # Set TTL only on first increment to avoid extending window on every request
        await redis.expire(key, 600)
    if count > 10:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Try again later.")
```

Also add `Request` to the existing fastapi import at the top of `deps.py` (`status` is already present):

```python
from fastapi import Depends, HTTPException, Request, status
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/deps.py
git commit -m "feat: add rate_limit dependency for IP-based request throttling"
```

---

### Task 3: Add `change-password` endpoint

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_auth.py`:

```python
def test_change_password_success(test_client):
    """CHANGE-PW-01: Authenticated user can change their own password."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "changepw@example.com", "password": "oldpassword1"},
    )
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": "changepw@example.com", "password": "oldpassword1"},
    )
    token = login_resp.json()["access_token"]

    resp = test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "oldpassword1", "new_password": "newpassword1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    # Verify old password no longer works
    old_login = test_client.post(
        "/api/v1/auth/login",
        json={"email": "changepw@example.com", "password": "oldpassword1"},
    )
    assert old_login.status_code == 401

    # Verify new password works
    new_login = test_client.post(
        "/api/v1/auth/login",
        json={"email": "changepw@example.com", "password": "newpassword1"},
    )
    assert new_login.status_code == 200


def test_change_password_wrong_current(test_client):
    """CHANGE-PW-02: Wrong current password returns 400."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "changepw2@example.com", "password": "oldpassword1"},
    )
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": "changepw2@example.com", "password": "oldpassword1"},
    )
    token = login_resp.json()["access_token"]

    resp = test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongcurrent", "new_password": "newpassword1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


def test_change_password_same_as_current(test_client):
    """CHANGE-PW-03: New password same as current returns 400."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "changepw3@example.com", "password": "samepassword1"},
    )
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": "changepw3@example.com", "password": "samepassword1"},
    )
    token = login_resp.json()["access_token"]

    resp = test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "samepassword1", "new_password": "samepassword1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "differ" in resp.json()["detail"].lower()


def test_change_password_unauthenticated(test_client):
    """CHANGE-PW-04: No token returns 401."""
    resp = test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "old", "new_password": "newpassword1"},
    )
    assert resp.status_code == 401


def test_change_password_too_short(test_client):
    """CHANGE-PW-05: new_password shorter than 8 chars returns 422."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "changepw5@example.com", "password": "oldpassword1"},
    )
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": "changepw5@example.com", "password": "oldpassword1"},
    )
    token = login_resp.json()["access_token"]

    resp = test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "oldpassword1", "new_password": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_auth.py -v -k "change_password"
```

Expected: FAIL — endpoint does not exist yet (404).

- [ ] **Step 3: Add `ChangePasswordRequest` schema to `backend/app/schemas/auth.py`**

Append after `TokenResponse`:

```python
class ChangePasswordRequest(BaseModel):
    """Request body for changing the authenticated user's password."""

    current_password: str
    new_password: str = Field(min_length=8)
```

- [ ] **Step 4: Add `change-password` endpoint to `backend/app/api/routes/auth.py`**

Make two import changes at the top of `auth.py`:

1. **Add** a new line: `from app.api.deps import get_current_user` (this import does not yet exist in the file).
2. **Replace** the existing `from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse` line with:

```python
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
```

Then append the new endpoint after the existing `refresh_token` route:

```python
@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change the authenticated user's password.

    Requires the correct current password. New password must differ from current.
    """
    if not current_user.password_hash or not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Plaintext-to-plaintext comparison (both from request body — not hash comparison)
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password",
        )

    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_auth.py -v -k "change_password"
```

Expected: all 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/routes/auth.py backend/tests/test_auth.py
git commit -m "feat: add change-password endpoint (authenticated, argon2id)"
```

---

### Task 4: Add `reset-password` endpoint

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_reset_password_success(test_client, async_session, mock_redis):
    """RESET-PW-01: Valid token resets password and is consumed (single-use)."""
    import hmac
    from app.main import app
    from app.core.redis import get_redis
    from app.api.deps import rate_limit

    async def override_redis():
        return mock_redis

    async def override_rate_limit():
        return None  # disable rate limiting in tests

    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[rate_limit] = override_rate_limit
    try:
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "resetpw@example.com", "password": "oldpassword1"},
        )

        # Seed a valid reset token in fakeredis
        await mock_redis.set("pwreset:resetpw@example.com", "ABCD1234", ex=3600)

        resp = test_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "resetpw@example.com",
                "token": "ABCD1234",
                "new_password": "brandnewpass1",
            },
        )
        assert resp.status_code == 204

        # Token must be deleted (single-use)
        stored = await mock_redis.get("pwreset:resetpw@example.com")
        assert stored is None

        # New password works
        login = test_client.post(
            "/api/v1/auth/login",
            json={"email": "resetpw@example.com", "password": "brandnewpass1"},
        )
        assert login.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(test_client, mock_redis):
    """RESET-PW-02: Wrong token returns 400 with generic message."""
    from app.main import app
    from app.core.redis import get_redis
    from app.api.deps import rate_limit

    async def override_redis():
        return mock_redis

    async def override_rate_limit():
        return None

    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[rate_limit] = override_rate_limit
    try:
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "resetpw2@example.com", "password": "oldpassword1"},
        )
        await mock_redis.set("pwreset:resetpw2@example.com", "CORRECT1", ex=3600)

        resp = test_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "resetpw2@example.com",
                "token": "WRONGTOK",
                "new_password": "newpassword1",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired reset token"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_password_no_token_in_redis(test_client, mock_redis):
    """RESET-PW-03: No token in Redis (expired or never set) returns 400."""
    from app.main import app
    from app.core.redis import get_redis
    from app.api.deps import rate_limit

    async def override_redis():
        return mock_redis

    async def override_rate_limit():
        return None

    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[rate_limit] = override_rate_limit
    try:
        resp = test_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "nobody@example.com",
                "token": "ANYTHING",
                "new_password": "newpassword1",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired reset token"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_password_too_short(test_client, mock_redis):
    """RESET-PW-04: new_password < 8 chars returns 422."""
    from app.main import app
    from app.core.redis import get_redis
    from app.api.deps import rate_limit

    async def override_redis():
        return mock_redis

    async def override_rate_limit():
        return None

    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[rate_limit] = override_rate_limit
    try:
        resp = test_client.post(
            "/api/v1/auth/reset-password",
            json={"email": "x@example.com", "token": "ABCD1234", "new_password": "short"},
        )
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_auth.py -v -k "reset_password"
```

Expected: FAIL — endpoint does not exist yet.

- [ ] **Step 3: Add `ResetPasswordRequest` schema to `backend/app/schemas/auth.py`**

Append after `ChangePasswordRequest`:

```python
class ResetPasswordRequest(BaseModel):
    """Request body for resetting a forgotten password via admin-issued token."""

    email: EmailStr
    token: str
    new_password: str = Field(min_length=8)
```

- [ ] **Step 4: Add `reset-password` endpoint to `backend/app/api/routes/auth.py`**

Add to imports at top of `auth.py`:

```python
import hmac

from app.api.deps import get_current_user, rate_limit
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
```

Append the endpoint after `change_password`:

```python
@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    _: None = Depends(rate_limit),
) -> None:
    """Reset a forgotten password using an admin-issued one-time token.

    Returns the same error for missing token and wrong token — no email enumeration.
    Token comparison uses hmac.compare_digest to prevent timing side-channels.
    """
    _invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token",
    )

    stored_token: str | None = await redis.get(f"pwreset:{body.email}")
    if stored_token is None:
        raise _invalid

    # Decode bytes if Redis returns bytes
    if isinstance(stored_token, bytes):
        stored_token = stored_token.decode()

    if not hmac.compare_digest(stored_token, body.token):
        raise _invalid

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise _invalid  # same error — no enumeration

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    # Consume the token (single-use)
    await redis.delete(f"pwreset:{body.email}")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_auth.py -v -k "reset_password"
```

Expected: all 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/routes/auth.py backend/tests/test_auth.py
git commit -m "feat: add reset-password endpoint with hmac comparison and rate limiting"
```

---

### Task 5: Create admin router with `reset-token` endpoint

**Files:**
- Create: `backend/app/api/routes/admin.py`
- Create: `backend/app/schemas/admin.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_admin.py`:

```python
"""Admin endpoint tests."""
import pytest


def _register_and_login(test_client, email: str, password: str = "securepass1") -> str:
    """Helper: register user and return access token."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_generate_reset_token_success(test_client, async_session, mock_redis):
    """ADMIN-01: Admin can generate a reset token for a registered user."""
    from app.main import app
    from app.core.redis import get_redis
    from sqlalchemy import select
    from app.models.user import User

    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis
    try:
        # Register target student
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "student_target@example.com", "password": "securepass1"},
        )

        # Register admin and elevate role via shared DB session
        admin_token = _register_and_login(test_client, "admin_user@example.com")
        result = await async_session.execute(
            select(User).where(User.email == "admin_user@example.com")
        )
        admin = result.scalar_one()
        admin.role = "admin"
        await async_session.commit()
        # Re-login to get a fresh token reflecting no role change in JWT
        # (role is checked live from DB by require_role, so token doesn't need re-issue)

        resp = test_client.post(
            "/api/v1/admin/reset-token",
            json={"email": "student_target@example.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) == 8
        assert data["token"].isalnum()
        assert data["token"] == data["token"].upper()
        assert data["expires_in_seconds"] == 3600

        # Token must be stored in Redis
        stored = await mock_redis.get(f"pwreset:student_target@example.com")
        assert stored is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_reset_token_forbidden_for_student(test_client, mock_redis):
    """ADMIN-02: Student role gets 403 Forbidden."""
    from app.main import app
    from app.core.redis import get_redis

    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis
    try:
        student_token = _register_and_login(test_client, "student_forbidden@example.com")
        resp = test_client.post(
            "/api/v1/admin/reset-token",
            json={"email": "anyone@example.com"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_reset_token_unknown_email(test_client, async_session, mock_redis):
    """ADMIN-03: Unknown email returns 404 (intentional admin-only exception)."""
    from app.main import app
    from app.core.redis import get_redis
    from sqlalchemy import select
    from app.models.user import User

    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis
    try:
        admin_token = _register_and_login(test_client, "admin_user2@example.com")
        result = await async_session.execute(
            select(User).where(User.email == "admin_user2@example.com")
        )
        admin = result.scalar_one()
        admin.role = "admin"
        await async_session.commit()

        resp = test_client.post(
            "/api/v1/admin/reset-token",
            json={"email": "doesnotexist@example.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_reset_token_overwrites_existing(test_client, async_session, mock_redis):
    """ADMIN-04: Second call overwrites previous token for same email."""
    from app.main import app
    from app.core.redis import get_redis
    from sqlalchemy import select
    from app.models.user import User

    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis
    try:
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "overwrite_target@example.com", "password": "securepass1"},
        )
        admin_token = _register_and_login(test_client, "admin_user3@example.com")
        result = await async_session.execute(
            select(User).where(User.email == "admin_user3@example.com")
        )
        admin = result.scalar_one()
        admin.role = "admin"
        await async_session.commit()

        resp1 = test_client.post(
            "/api/v1/admin/reset-token",
            json={"email": "overwrite_target@example.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        token1 = resp1.json()["token"]

        resp2 = test_client.post(
            "/api/v1/admin/reset-token",
            json={"email": "overwrite_target@example.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        token2 = resp2.json()["token"]

        stored = await mock_redis.get("pwreset:overwrite_target@example.com")
        if isinstance(stored, bytes):
            stored = stored.decode()
        assert stored == token2  # latest token wins

        # Verify old token (token1) is now rejected by reset-password
        from app.api.deps import rate_limit

        async def override_rate_limit():
            return None

        app.dependency_overrides[rate_limit] = override_rate_limit
        reject_resp = test_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "overwrite_target@example.com",
                "token": token1,
                "new_password": "brandnewpass1",
            },
        )
        # token1 is rejected because Redis now holds token2
        assert reject_resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_admin.py -v
```

Expected: FAIL — router not registered, endpoint doesn't exist.

- [ ] **Step 3: Create `backend/app/schemas/admin.py`**

```python
"""Pydantic schemas for admin endpoints."""
from pydantic import BaseModel, EmailStr


class GenerateResetTokenRequest(BaseModel):
    """Request body to generate a password reset token for a user."""

    email: EmailStr


class ResetTokenResponse(BaseModel):
    """Response carrying the generated reset token."""

    token: str
    expires_in_seconds: int
```

- [ ] **Step 4: Create `backend/app/api/routes/admin.py`**

```python
"""Admin-only endpoints."""
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.admin import GenerateResetTokenRequest, ResetTokenResponse

router = APIRouter()

_RESET_TOKEN_TTL = 3600  # 1 hour
_TOKEN_ALPHABET = string.ascii_uppercase + string.digits


@router.post("/reset-token", response_model=ResetTokenResponse)
async def generate_reset_token(
    body: GenerateResetTokenRequest,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ResetTokenResponse:
    """Generate a one-time password reset token for a user (admin only).

    A repeated call for the same email overwrites the previous token.
    Returns 404 if the email is not registered — intentional admin-only exception.

    SECURITY: Do not enable DEBUG-level response body logging for this endpoint.
    Communicate the token to the student out-of-band.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token = "".join(secrets.choice(_TOKEN_ALPHABET) for _ in range(8))
    await redis.set(f"pwreset:{body.email}", token, ex=_RESET_TOKEN_TTL)

    return ResetTokenResponse(token=token, expires_in_seconds=_RESET_TOKEN_TTL)
```

- [ ] **Step 5: Register admin router in `backend/app/main.py`**

After the last `app.include_router` call, append:

```python
# --- Admin routes ---
from app.api.routes.admin import router as admin_router

app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
```

- [ ] **Step 6: Run all backend tests to verify they pass**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest tests/test_admin.py tests/test_auth.py tests/test_users.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/api/routes/admin.py backend/app/main.py backend/tests/test_admin.py
git commit -m "feat: add admin reset-token endpoint with 8-char uppercase alphanumeric token"
```

---

## Chunk 2: Frontend

### Task 6: Extend `api/auth.ts` and create `api/admin.ts`

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/admin.ts`

No isolated tests for API modules — they are covered by component tests.

- [ ] **Step 1: Add `changePassword` and `resetPassword` to `frontend/src/api/auth.ts`**

Append after the `getMe` function:

```typescript
/**
 * Change the authenticated user's password.
 * Throws on 400 (wrong current password / same password) or 422 (too short).
 */
export async function changePassword(
  current_password: string,
  new_password: string
): Promise<void> {
  await apiClient.post("/auth/change-password", { current_password, new_password });
}

/**
 * Reset a forgotten password using an admin-issued one-time token.
 * Throws on 400 (invalid/expired token) or 422 (too short).
 */
export async function resetPassword(
  email: string,
  token: string,
  new_password: string
): Promise<void> {
  await apiClient.post("/auth/reset-password", { email, token, new_password });
}
```

- [ ] **Step 2: Create `frontend/src/api/admin.ts`**

```typescript
import { apiClient } from "./client";

/**
 * Generate a one-time password reset token for a user (admin only).
 * Returns the token and its TTL in seconds.
 */
export async function generateResetToken(
  email: string
): Promise<{ token: string; expires_in_seconds: number }> {
  const { data } = await apiClient.post<{ token: string; expires_in_seconds: number }>(
    "/admin/reset-token",
    { email }
  );
  return data;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/auth.ts frontend/src/api/admin.ts
git commit -m "feat: add changePassword/resetPassword API functions and admin.ts"
```

---

### Task 7: Create `AppHeader` component

**Files:**
- Create: `frontend/src/components/AppHeader/AppHeader.tsx`
- Create: `frontend/src/components/AppHeader/AppHeader.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/AppHeader/AppHeader.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AppHeader } from "./AppHeader";

// Stub logout so tests don't hit the network
vi.mock("../../api/auth", () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}));

// Minimal Zustand store mock
vi.mock("../../store", () => ({
  useStore: (selector: (s: unknown) => unknown) => {
    const state = {
      user: {
        email: "test@example.com",
        display_name: "Test User",
        storage_used_bytes: 500_000_000,
        storage_quota_bytes: null,
      },
      clearAuth: vi.fn(),
    };
    return selector(state);
  },
}));

function renderHeader(props = {}) {
  return render(
    <MemoryRouter>
      <AppHeader {...props} />
    </MemoryRouter>
  );
}

describe("AppHeader", () => {
  it("shows the ChipAtelier branding", () => {
    renderHeader();
    expect(screen.getByText("ChipAtelier")).toBeTruthy();
  });

  it("shows storage usage chip with used / quota", () => {
    renderHeader();
    // quota is null → falls back to DEFAULT_QUOTA_GB constant
    expect(screen.getByText(/0\.5 GB of \d+ GB used/)).toBeTruthy();
  });

  it("shows user display name in dropdown trigger", () => {
    renderHeader();
    expect(screen.getByText("Test User")).toBeTruthy();
  });

  it("dropdown opens on click and shows email, Change Password, Sign out", () => {
    renderHeader();
    fireEvent.click(screen.getByText("Test User"));
    expect(screen.getByText("test@example.com")).toBeTruthy();
    expect(screen.getByText("Change Password")).toBeTruthy();
    expect(screen.getByText("Sign out")).toBeTruthy();
  });

  it("renders breadcrumbs slot when provided", () => {
    renderHeader({ breadcrumbs: <span>Projects &gt; my-design</span> });
    expect(screen.getByText(/Projects/)).toBeTruthy();
  });

  it("renders actions slot when provided", () => {
    renderHeader({ actions: <button>New Project</button> });
    expect(screen.getByText("New Project")).toBeTruthy();
  });

  it("calls onChangePassword when Change Password item is clicked", () => {
    const onChangePassword = vi.fn();
    renderHeader({ onChangePassword });
    fireEvent.click(screen.getByText("Test User"));
    fireEvent.click(screen.getByText("Change Password"));
    expect(onChangePassword).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/components/AppHeader/AppHeader.test.tsx
```

Expected: FAIL — component does not exist.

- [ ] **Step 3: Create `frontend/src/components/AppHeader/AppHeader.tsx`**

```typescript
import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { logout as authLogout } from "../../api/auth";
import { useStore } from "../../store";
import { DEFAULT_QUOTA_GB } from "../../constants";

export interface AppHeaderProps {
  breadcrumbs?: React.ReactNode;
  actions?: React.ReactNode;
  onChangePassword?: () => void;
}

const HEADER: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 16,
  padding: "12px 24px",
  borderBottom: "1px solid #30363d",
  background: "#161b22",
  position: "relative",
};

const LOGO: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#f0f6fc",
  textDecoration: "none",
  flexShrink: 0,
};

const BREADCRUMB_WRAP: React.CSSProperties = {
  flex: 1,
  fontSize: 13,
  color: "#8b949e",
};

const STORAGE_CHIP: React.CSSProperties = {
  fontSize: 12,
  color: "#8b949e",
  background: "#0d1117",
  border: "1px solid #30363d",
  borderRadius: 6,
  padding: "4px 10px",
  flexShrink: 0,
};

const DROPDOWN_BTN: React.CSSProperties = {
  background: "none",
  border: "1px solid #30363d",
  borderRadius: 6,
  color: "#c9d1d9",
  padding: "6px 12px",
  fontSize: 13,
  cursor: "pointer",
  flexShrink: 0,
};

const DROPDOWN_MENU: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  right: 24,
  marginTop: 4,
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 8,
  minWidth: 220,
  zIndex: 100,
  boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
};

const DROPDOWN_EMAIL: React.CSSProperties = {
  padding: "12px 16px 8px",
  fontSize: 12,
  color: "#8b949e",
  borderBottom: "1px solid #21262d",
};

const DROPDOWN_ITEM: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "10px 16px",
  background: "none",
  border: "none",
  textAlign: "left",
  fontSize: 13,
  color: "#c9d1d9",
  cursor: "pointer",
};

const DROPDOWN_DIVIDER: React.CSSProperties = {
  borderTop: "1px solid #21262d",
  margin: "4px 0",
};

export function AppHeader({ breadcrumbs, actions, onChangePassword }: AppHeaderProps): React.ReactElement {
  const navigate = useNavigate();
  const user = useStore((s) => s.user);
  const clearAuth = useStore((s) => s.clearAuth);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const storageGB = user ? (user.storage_used_bytes / 1e9).toFixed(1) : "0.0";
  const quotaGB = user?.storage_quota_bytes
    ? (user.storage_quota_bytes / 1e9).toFixed(0)
    : String(DEFAULT_QUOTA_GB);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent): void {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function handleSignOut(): void {
    setOpen(false);
    authLogout()
      .catch(() => undefined)
      .finally(() => {
        clearAuth();
        navigate("/login");
      });
  }

  function handleChangePassword(): void {
    setOpen(false);
    onChangePassword?.();
  }

  return (
    <header style={HEADER}>
      <Link to="/projects" style={LOGO}>
        ChipAtelier
      </Link>

      {breadcrumbs && <div style={BREADCRUMB_WRAP}>{breadcrumbs}</div>}
      {!breadcrumbs && <div style={{ flex: 1 }} />}

      {actions}

      <span style={STORAGE_CHIP}>{storageGB} of {quotaGB} GB used</span>

      <div ref={menuRef} style={{ position: "relative" }}>
        <button style={DROPDOWN_BTN} onClick={() => setOpen((v) => !v)}>
          {user?.display_name ?? user?.email ?? "Account"}
        </button>

        {open && (
          <div style={DROPDOWN_MENU}>
            <div style={DROPDOWN_EMAIL}>{user?.email}</div>
            <button
              style={DROPDOWN_ITEM}
              onClick={handleChangePassword}
            >
              Change Password
            </button>
            <div style={DROPDOWN_DIVIDER} />
            <button style={{ ...DROPDOWN_ITEM, color: "#f85149" }} onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/components/AppHeader/AppHeader.test.tsx
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AppHeader/
git commit -m "feat: add AppHeader component with user dropdown, storage chip, breadcrumbs slot"
```

---

### Task 8: Create `ChangePasswordModal` component

**Files:**
- Create: `frontend/src/components/ChangePasswordModal/ChangePasswordModal.tsx`
- Create: `frontend/src/components/ChangePasswordModal/ChangePasswordModal.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ChangePasswordModal/ChangePasswordModal.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ChangePasswordModal } from "./ChangePasswordModal";

vi.mock("../../api/auth", () => ({
  changePassword: vi.fn(),
}));

import { changePassword } from "../../api/auth";

describe("ChangePasswordModal", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <ChangePasswordModal open={false} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders form fields when open", () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    expect(screen.getByLabelText("Current password")).toBeTruthy();
    expect(screen.getByLabelText("New password")).toBeTruthy();
    expect(screen.getByLabelText("Confirm new password")).toBeTruthy();
  });

  it("shows error when new password is shorter than 8 chars", async () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "current1" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "short" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "short" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(screen.getByText(/at least 8/i)).toBeTruthy();
    });
  });

  it("shows error when passwords do not match", async () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "current1" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpassword1" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "differentpass1" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(screen.getByText(/do not match/i)).toBeTruthy();
    });
  });

  it("shows error when new equals current", async () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "samepass1" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "samepass1" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "samepass1" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(screen.getByText(/must differ/i)).toBeTruthy();
    });
  });

  it("calls changePassword API, shows success, then calls onClose after 1.5 s", async () => {
    vi.useFakeTimers();
    const onClose = vi.fn();
    vi.mocked(changePassword).mockResolvedValueOnce(undefined);

    render(<ChangePasswordModal open={true} onClose={onClose} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "oldpass1!" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass1!" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "newpass1!" } });
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledWith("oldpass1!", "newpass1!");
    });
    await waitFor(() => {
      expect(screen.getByText(/password changed/i)).toBeTruthy();
    });

    // Advance past the 1.5 s auto-close timer
    vi.runAllTimers();
    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    vi.useRealTimers();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/components/ChangePasswordModal/ChangePasswordModal.test.tsx
```

Expected: FAIL — component does not exist.

- [ ] **Step 3: Create `frontend/src/components/ChangePasswordModal/ChangePasswordModal.tsx`**

```typescript
import React, { useState } from "react";
import { changePassword } from "../../api/auth";

export interface ChangePasswordModalProps {
  open: boolean;
  onClose: () => void;
}

const OVERLAY: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 200,
};

const CARD: React.CSSProperties = {
  width: "100%",
  maxWidth: 420,
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 12,
  padding: 28,
};

const HEADING: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#e6edf3",
  marginBottom: 20,
};

const LABEL: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 500,
  color: "#8b949e",
  marginBottom: 4,
};

const INPUT: React.CSSProperties = {
  width: "100%",
  borderRadius: 6,
  border: "1px solid #30363d",
  background: "#0d1117",
  color: "#e6edf3",
  padding: "8px 12px",
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
};

const BTN_PRIMARY: React.CSSProperties = {
  borderRadius: 6,
  background: "#238636",
  color: "#fff",
  padding: "8px 16px",
  fontSize: 14,
  fontWeight: 600,
  border: "none",
  cursor: "pointer",
};

const BTN_SECONDARY: React.CSSProperties = {
  borderRadius: 6,
  background: "none",
  color: "#8b949e",
  padding: "8px 16px",
  fontSize: 14,
  border: "1px solid #30363d",
  cursor: "pointer",
};

const ERROR_BOX: React.CSSProperties = {
  borderRadius: 6,
  background: "#3d1f1f",
  border: "1px solid #6e3630",
  color: "#f85149",
  padding: "10px 14px",
  fontSize: 13,
  marginBottom: 16,
};

const SUCCESS_BOX: React.CSSProperties = {
  borderRadius: 6,
  background: "#1a3a25",
  border: "1px solid #2ea043",
  color: "#3fb950",
  padding: "10px 14px",
  fontSize: 13,
  marginBottom: 16,
};

export function ChangePasswordModal({ open, onClose }: ChangePasswordModalProps): React.ReactElement | null {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  function reset(): void {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError(null);
    setSuccess(false);
    setLoading(false);
  }

  function handleClose(): void {
    reset();
    onClose();
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError(null);

    if (next.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (next === current) {
      setError("New password must differ from current password.");
      return;
    }

    setLoading(true);
    try {
      await changePassword(current, next);
      setSuccess(true);
      setTimeout(() => {
        reset();
        onClose();
      }, 1500);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail ?? "Failed to change password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={OVERLAY} onClick={handleClose}>
      <div style={CARD} onClick={(e) => e.stopPropagation()}>
        <h2 style={HEADING}>Change Password</h2>

        {error && <div style={ERROR_BOX}>{error}</div>}
        {success && <div style={SUCCESS_BOX}>Password changed successfully.</div>}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label htmlFor="cpw-current" style={LABEL}>Current password</label>
            <input
              id="cpw-current"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              style={INPUT}
              aria-label="Current password"
            />
          </div>
          <div>
            <label htmlFor="cpw-new" style={LABEL}>New password</label>
            <input
              id="cpw-new"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              style={INPUT}
              aria-label="New password"
            />
          </div>
          <div>
            <label htmlFor="cpw-confirm" style={LABEL}>Confirm new password</label>
            <input
              id="cpw-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              style={INPUT}
              aria-label="Confirm new password"
            />
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
            <button type="button" style={BTN_SECONDARY} onClick={handleClose}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || success}
              style={{ ...BTN_PRIMARY, opacity: loading || success ? 0.6 : 1, cursor: loading || success ? "not-allowed" : "pointer" }}
            >
              {loading ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/components/ChangePasswordModal/ChangePasswordModal.test.tsx
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChangePasswordModal/
git commit -m "feat: add ChangePasswordModal with client-side validation and loading state"
```

---

### Task 9: Migrate protected pages to use `AppHeader`

**Files:**
- Modify: `frontend/src/pages/ProjectListPage.tsx`
- Modify: `frontend/src/pages/ProjectPage.tsx`
- Modify: `frontend/src/pages/RunDetailPage.tsx`

No new tests — existing page behaviour is unchanged; the header is now a shared component.

- [ ] **Step 1: Update `ProjectListPage.tsx`**

Add imports at the top:
```typescript
import { AppHeader } from "../components/AppHeader/AppHeader";
import { ChangePasswordModal } from "../components/ChangePasswordModal/ChangePasswordModal";
```

Add state inside the component (alongside existing state):
```typescript
const [changePwOpen, setChangePwOpen] = useState(false);
```

Replace the existing `<header>...</header>` block (the one with "ChipAtelier" branding, storage chip, and Sign out button) with:
```typescript
<AppHeader
  actions={
    <button
      style={{
        borderRadius: 6,
        background: "#238636",
        color: "#fff",
        padding: "8px 14px",
        fontSize: 13,
        fontWeight: 600,
        border: "none",
        cursor: "pointer",
      }}
      onClick={() => setShowNewProjectForm(true)}
    >
      + New Project
    </button>
  }
  onChangePassword={() => setChangePwOpen(true)}
/>
<ChangePasswordModal open={changePwOpen} onClose={() => setChangePwOpen(false)} />
```

Remove the old `handleLogout` function (logout is now inside `AppHeader`), and remove the `logout as authLogout` import and the `clearAuth` store selector (both moved to `AppHeader`). Keep the `useNavigate` / `navigate` variable — it is still used for card-click navigation to `/projects/{id}`.

- [ ] **Step 2: Update `ProjectPage.tsx`**

Add imports:
```typescript
import { AppHeader } from "../components/AppHeader/AppHeader";
import { ChangePasswordModal } from "../components/ChangePasswordModal/ChangePasswordModal";
```

Add state:
```typescript
const [changePwOpen, setChangePwOpen] = useState(false);
```

Replace the existing breadcrumb `<header>` or top-of-page nav section with:
```typescript
<AppHeader
  breadcrumbs={
    <span style={{ color: "#8b949e" }}>
      <Link to="/projects" style={{ color: "#58a6ff", textDecoration: "none" }}>Projects</Link>
      {" › "}
      <span style={{ color: "#e6edf3" }}>{project?.name ?? "…"}</span>
    </span>
  }
  onChangePassword={() => setChangePwOpen(true)}
/>
<ChangePasswordModal open={changePwOpen} onClose={() => setChangePwOpen(false)} />
```

Remove any existing import of `logout` and `clearAuth` if present in this file.

- [ ] **Step 3: Update `RunDetailPage.tsx`**

Add imports:
```typescript
import { AppHeader } from "../components/AppHeader/AppHeader";
import { ChangePasswordModal } from "../components/ChangePasswordModal/ChangePasswordModal";
```

Add state:
```typescript
const [changePwOpen, setChangePwOpen] = useState(false);
```

Replace the existing breadcrumb section with:
```typescript
<AppHeader
  breadcrumbs={
    <span style={{ color: "#8b949e" }}>
      <Link to="/projects" style={{ color: "#58a6ff", textDecoration: "none" }}>Projects</Link>
      {" › "}
      <Link
        to={`/projects/${projectId}`}
        style={{ color: "#58a6ff", textDecoration: "none" }}
      >
        {projectName || "…"}
      </Link>
      {" › "}
      <span style={{ color: "#e6edf3" }}>Run #{run?.run_number ?? "…"}</span>
    </span>
  }
  onChangePassword={() => setChangePwOpen(true)}
/>
<ChangePasswordModal open={changePwOpen} onClose={() => setChangePwOpen(false)} />
```

- [ ] **Step 4: Verify the app builds with no TypeScript errors**

```bash
cd /opt/apps/chipatelier/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ProjectListPage.tsx frontend/src/pages/ProjectPage.tsx frontend/src/pages/RunDetailPage.tsx
git commit -m "feat: adopt AppHeader with user dropdown on all protected pages"
```

---

### Task 10: Update `LoginPage` — forgot password link + flash message

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/LoginPage.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LoginPage from "./LoginPage";

vi.mock("../api/auth", () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}));

vi.mock("../store", () => ({
  useStore: (selector: (s: unknown) => unknown) =>
    selector({ setAuth: vi.fn() }),
}));

describe("LoginPage", () => {
  it("renders Forgot your password link", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Forgot your password/i)).toBeTruthy();
  });

  it("shows flash message when location state contains flash", () => {
    render(
      <MemoryRouter
        initialEntries={[{ pathname: "/login", state: { flash: "Password reset successfully. Please sign in." } }]}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Password reset successfully/i)).toBeTruthy();
  });

  it("does not show flash banner without location state", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.queryByText(/Password reset successfully/i)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/pages/LoginPage.test.tsx
```

Expected: FAIL — no "Forgot your password" link or flash banner.

- [ ] **Step 3: Update `LoginPage.tsx`**

Add to imports:
```typescript
import { useEffect } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
```

Add inside the component, before the `useState` calls:
```typescript
const location = useLocation();
const flash = (location.state as { flash?: string } | null)?.flash ?? null;

// Clear flash from history so back-navigation doesn't re-show it
useEffect(() => {
  if (flash) {
    window.history.replaceState({}, document.title);
  }
}, []); // eslint-disable-line react-hooks/exhaustive-deps
```

Add the flash banner just before the `{error && ...}` block inside the return:
```typescript
{flash && (
  <div
    style={{
      marginBottom: 16,
      borderRadius: 6,
      background: "#1a3a25",
      border: "1px solid #2ea043",
      color: "#3fb950",
      padding: "12px 16px",
      fontSize: 13,
    }}
  >
    {flash}
  </div>
)}
```

Add the "Forgot your password?" link after the submit button inside the `<form>`:
```typescript
<p style={{ margin: 0, fontSize: 13, textAlign: "center", color: "#8b949e" }}>
  <Link to="/reset-password" style={LINK}>
    Forgot your password?
  </Link>
</p>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/pages/LoginPage.test.tsx
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx frontend/src/pages/LoginPage.test.tsx
git commit -m "feat: add forgot password link and flash message to LoginPage"
```

---

### Task 11: Create `ResetPasswordPage`

**Files:**
- Create: `frontend/src/pages/ResetPasswordPage.tsx`
- Create: `frontend/src/pages/ResetPasswordPage.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/ResetPasswordPage.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ResetPasswordPage from "./ResetPasswordPage";

vi.mock("../api/auth", () => ({
  resetPassword: vi.fn(),
}));

import { resetPassword } from "../api/auth";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/reset-password"]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ResetPasswordPage", () => {
  it("renders email, token, and new password fields", () => {
    renderPage();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Reset token")).toBeTruthy();
    expect(screen.getByLabelText("New password")).toBeTruthy();
  });

  it("renders link back to login", () => {
    renderPage();
    expect(screen.getByText(/Back to sign in/i)).toBeTruthy();
  });

  it("shows error on API failure", async () => {
    vi.mocked(resetPassword).mockRejectedValueOnce({
      response: { data: { detail: "Invalid or expired reset token" } },
    });
    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "u@example.com" } });
    fireEvent.change(screen.getByLabelText("Reset token"), { target: { value: "ABCD1234" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpassword1" } });
    fireEvent.click(screen.getByText("Reset password"));
    await waitFor(() => {
      expect(screen.getByText(/Invalid or expired reset token/i)).toBeTruthy();
    });
  });

  it("navigates to /login with flash on success", async () => {
    vi.mocked(resetPassword).mockResolvedValueOnce(undefined);
    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "u@example.com" } });
    fireEvent.change(screen.getByLabelText("Reset token"), { target: { value: "ABCD1234" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpassword1" } });
    fireEvent.click(screen.getByText("Reset password"));
    await waitFor(() => {
      expect(screen.getByText("Login Page")).toBeTruthy();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/pages/ResetPasswordPage.test.tsx
```

Expected: FAIL — page does not exist.

- [ ] **Step 3: Create `frontend/src/pages/ResetPasswordPage.tsx`**

```typescript
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { resetPassword } from "../api/auth";

// Reuse LoginPage style tokens
const PAGE_BG: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "#0d1117",
};

const CARD: React.CSSProperties = {
  width: "100%",
  maxWidth: 420,
  background: "#161b22",
  borderRadius: 12,
  border: "1px solid #30363d",
  padding: 32,
};

const HEADING: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 700,
  color: "#e6edf3",
  marginBottom: 8,
};

const SUBTITLE: React.CSSProperties = {
  fontSize: 13,
  color: "#8b949e",
  marginBottom: 24,
};

const ERROR_BOX: React.CSSProperties = {
  marginBottom: 16,
  borderRadius: 6,
  background: "#3d1f1f",
  border: "1px solid #6e3630",
  color: "#f85149",
  padding: "12px 16px",
  fontSize: 13,
};

const LABEL: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 500,
  color: "#8b949e",
  marginBottom: 4,
};

const INPUT: React.CSSProperties = {
  width: "100%",
  borderRadius: 6,
  border: "1px solid #30363d",
  background: "#0d1117",
  color: "#e6edf3",
  padding: "8px 12px",
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
};

const BUTTON: React.CSSProperties = {
  width: "100%",
  borderRadius: 6,
  background: "#238636",
  color: "#ffffff",
  padding: "10px 16px",
  fontSize: 14,
  fontWeight: 600,
  border: "none",
  cursor: "pointer",
};

const FOOTER: React.CSSProperties = {
  marginTop: 16,
  fontSize: 13,
  textAlign: "center",
  color: "#8b949e",
};

const LINK: React.CSSProperties = {
  color: "#58a6ff",
  textDecoration: "none",
};

export default function ResetPasswordPage(): React.ReactElement {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await resetPassword(email, token, newPassword);
      navigate("/login", {
        state: { flash: "Password reset successfully. Please sign in." },
      });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail ?? "Invalid or expired token.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={PAGE_BG}>
      <div style={CARD}>
        <h1 style={HEADING}>Reset your password</h1>
        <p style={SUBTITLE}>Enter your email, the token your instructor provided, and your new password.</p>

        {error && <div style={ERROR_BOX}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label htmlFor="rp-email" style={LABEL}>Email</label>
            <input
              id="rp-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              style={INPUT}
              aria-label="Email"
            />
          </div>

          <div>
            <label htmlFor="rp-token" style={LABEL}>Reset token</label>
            <input
              id="rp-token"
              type="text"
              value={token}
              onChange={(e) => setToken(e.target.value.toUpperCase())}
              required
              maxLength={8}
              placeholder="8-character token from your instructor"
              style={{ ...INPUT, letterSpacing: "0.1em", fontFamily: "monospace" }}
              aria-label="Reset token"
            />
          </div>

          <div>
            <label htmlFor="rp-newpw" style={LABEL}>New password</label>
            <input
              id="rp-newpw"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              style={INPUT}
              aria-label="New password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{ ...BUTTON, opacity: loading ? 0.6 : 1, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "Resetting..." : "Reset password"}
          </button>
        </form>

        <p style={FOOTER}>
          <Link to="/login" style={LINK}>
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run src/pages/ResetPasswordPage.test.tsx
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ResetPasswordPage.tsx frontend/src/pages/ResetPasswordPage.test.tsx
git commit -m "feat: add ResetPasswordPage with admin-token reset flow"
```

---

### Task 12: Register `/reset-password` route in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add import and route**

Add to imports at top of `App.tsx`:
```typescript
import ResetPasswordPage from "./pages/ResetPasswordPage";
```

In the `<Routes>` block, add after the `/register` route:
```typescript
<Route path="/reset-password" element={<ResetPasswordPage />} />
```

- [ ] **Step 2: Verify TypeScript builds cleanly**

```bash
cd /opt/apps/chipatelier/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run the full frontend test suite**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run
```

Expected: all tests PASS (including new tests from Tasks 7–11).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: register /reset-password public route in App.tsx"
```

---

### Final: Full regression

- [ ] **Run the complete backend test suite**

```bash
cd /opt/apps/chipatelier/backend && python -m pytest --tb=short -q
```

Expected: 218 + new tests PASS, 0 failures.

- [ ] **Run the complete frontend test suite**

```bash
cd /opt/apps/chipatelier/frontend && npx vitest run
```

Expected: all PASS.
