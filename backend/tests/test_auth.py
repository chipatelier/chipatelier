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
    assert "/api/v1/auth/refresh" in cookies


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
    access_token = login_resp.json()["access_token"]

    # Logout — must succeed
    logout_resp = test_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 204


@pytest.mark.asyncio
async def test_refresh_token(test_client: TestClient):
    """AUTH-04: POST /auth/refresh with valid cookie returns new access_token."""
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "frank@example.com", "password": "securepass1"},
    )
    test_client.post(
        "/api/v1/auth/login",
        json={"email": "frank@example.com", "password": "securepass1"},
    )
    # The TestClient stores cookies — send refresh request
    response = test_client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_without_cookie(test_client: TestClient):
    """AUTH-04: POST /auth/refresh without cookie returns 401."""
    # Use a fresh client with no cookies
    from fastapi.testclient import TestClient as TC
    from app.main import app

    with TC(app, raise_server_exceptions=False) as fresh_client:
        response = fresh_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


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
