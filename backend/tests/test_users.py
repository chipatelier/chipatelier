"""Wave 0 stub: user model and API tests — implemented in plan 01-02."""
import pytest


async def test_create_user(async_session):
    """User can be created and saved to database."""
    pass


async def test_user_email_unique(async_session):
    """Two users cannot share the same email address."""
    pass


async def test_user_storage_tracking(async_session):
    """User storage_used_bytes is updated when artifacts are stored."""
    pass
