"""Wave 0 stub: auth tests — implemented in plan 01-02."""
import pytest


async def test_register(test_client):
    """User registration endpoint creates account and returns tokens."""
    pass


async def test_login_returns_jwt_and_cookie(test_client):
    """Login returns access_token in body and refresh_token in httpOnly cookie."""
    pass


async def test_logout_invalidates_refresh(test_client, mock_redis):
    """Logout adds refresh token to deny-list in Redis."""
    pass


async def test_refresh_token(test_client):
    """POST /auth/refresh with valid cookie returns new access_token."""
    pass
