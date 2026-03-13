"""User API tests — DASH-04 storage usage and profile endpoint."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_user(async_session: AsyncSession):
    """User can be created and saved to database."""
    from app.models.user import User

    user = User(
        email="test_create@example.com",
        display_name="Test User",
        role="student",
        password_hash="$argon2id$v=19$...",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    assert user.id is not None
    assert user.email == "test_create@example.com"
    assert user.storage_used_bytes == 0


@pytest.mark.asyncio
async def test_user_email_unique(async_session: AsyncSession):
    """Two users cannot share the same email address."""
    from app.models.user import User
    from sqlalchemy.exc import IntegrityError

    user1 = User(email="unique_test@example.com", password_hash="hash1")
    user2 = User(email="unique_test@example.com", password_hash="hash2")
    async_session.add(user1)
    await async_session.commit()
    async_session.add(user2)
    with pytest.raises(IntegrityError):
        await async_session.commit()


@pytest.mark.asyncio
async def test_user_storage_tracking(async_session: AsyncSession):
    """User storage_used_bytes can be set and read back correctly."""
    from app.models.user import User

    user = User(
        email="storage_test@example.com",
        password_hash="hash",
        storage_used_bytes=1234567890,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    assert user.storage_used_bytes == 1234567890


@pytest.mark.asyncio
async def test_get_me_returns_storage(test_client: TestClient):
    """DASH-04: GET /users/me includes storage_used_bytes field."""
    # Register user
    test_client.post(
        "/api/v1/auth/register",
        json={"email": "me_test@example.com", "password": "securepass1", "display_name": "Me User"},
    )
    # Login to get token
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": "me_test@example.com", "password": "securepass1"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Get profile
    response = test_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me_test@example.com"
    assert data["display_name"] == "Me User"
    assert "storage_used_bytes" in data
    assert isinstance(data["storage_used_bytes"], int)
    assert "id" in data
    assert data["role"] == "student"
