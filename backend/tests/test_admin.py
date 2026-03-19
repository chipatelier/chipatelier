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
        assert not any(c in data["token"] for c in "0O1I"), "Token must not contain ambiguous chars"
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
        from app.api.routes.auth import _reset_rate_limit

        async def override_rate_limit():
            return None

        app.dependency_overrides[_reset_rate_limit] = override_rate_limit
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
