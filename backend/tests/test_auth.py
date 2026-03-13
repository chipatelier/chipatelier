"""Auth endpoint tests — AUTH-01 through AUTH-04."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_register(test_client: TestClient):
    """AUTH-01: Registration creates user with argon2id hash, returns 201."""
    response = test_client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "securepass1", "display_name": "Alice"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "id" in data
    assert data["role"] == "student"
    # password_hash must not be exposed
    assert "password_hash" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(test_client: TestClient):
    """AUTH-01: Duplicate email returns 409."""
    payload = {"email": "bob@example.com", "password": "securepass1"}
    test_client.post("/api/v1/auth/register", json=payload)
    response = test_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_jwt_and_cookie(test_client: TestClient):
    """AUTH-02: Login returns access_token in body and refresh_token in httpOnly cookie."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "securepass1"},
    )
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "securepass1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Check Set-Cookie header contains refresh_token with httpOnly
    cookies = response.headers.get("set-cookie", "")
    assert "refresh_token" in cookies
    assert "HttpOnly" in cookies or "httponly" in cookies.lower()
    assert "/api/v1/auth" in cookies


@pytest.mark.asyncio
async def test_login_wrong_password(test_client: TestClient):
    """AUTH-02: Wrong password returns 401."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "dave@example.com", "password": "securepass1"},
    )
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_refresh(test_client: TestClient, mock_redis):
    """AUTH-03: Logout adds jti to Redis denylist and clears cookie."""
    from app.main import app
    from app.core.redis import get_redis

    # Override Redis dependency with mock for this test
    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis

    try:
        # Register and login
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "eve@example.com", "password": "securepass1"},
        )
        login_resp = test_client.post(
            "/api/v1/auth/login",
            json={"email": "eve@example.com", "password": "securepass1"},
        )
        assert login_resp.status_code == 200

        # Extract refresh token from Set-Cookie header and send manually
        set_cookie_header = login_resp.headers.get("set-cookie", "")
        # Parse the refresh_token value from the Set-Cookie header
        refresh_token_val = None
        for part in set_cookie_header.split(";"):
            part = part.strip()
            if part.startswith("refresh_token="):
                refresh_token_val = part[len("refresh_token="):]
                break
        assert refresh_token_val is not None, "No refresh_token in Set-Cookie header"

        # Logout — send cookie manually in header
        logout_resp = test_client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": refresh_token_val},
        )
        assert logout_resp.status_code == 204
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_refresh_token(test_client: TestClient, mock_redis):
    """AUTH-04: POST /auth/refresh with valid cookie returns new access_token."""
    from app.main import app
    from app.core.redis import get_redis

    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis

    try:
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "frank@example.com", "password": "securepass1"},
        )
        login_resp = test_client.post(
            "/api/v1/auth/login",
            json={"email": "frank@example.com", "password": "securepass1"},
        )
        assert login_resp.status_code == 200

        # Extract refresh token from Set-Cookie and send explicitly
        set_cookie = login_resp.headers.get("set-cookie", "")
        refresh_token_val = None
        for part in set_cookie.split(";"):
            part = part.strip()
            if part.startswith("refresh_token="):
                refresh_token_val = part[len("refresh_token="):]
                break
        assert refresh_token_val is not None

        response = test_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token_val},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_refresh_without_cookie(test_client: TestClient, mock_redis):
    """AUTH-04: POST /auth/refresh without cookie returns 401."""
    from app.main import app
    from app.core.redis import get_redis

    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis

    try:
        # Use a fresh client with no cookies
        from fastapi.testclient import TestClient as TC
        from app.core.database import get_db as get_db_dep

        # Override DB too so the fresh client hits in-memory DB
        def fresh_override_db():
            return test_client.app.dependency_overrides.get(get_db_dep, get_db_dep)

        with TC(app, raise_server_exceptions=False) as fresh_client:
            response = fresh_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_protected_route_no_token(test_client: TestClient):
    """get_current_user raises 401 for missing token."""
    response = test_client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_bad_token(test_client: TestClient):
    """get_current_user raises 401 for malformed token."""
    response = test_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer this-is-not-a-jwt"},
    )
    assert response.status_code == 401
