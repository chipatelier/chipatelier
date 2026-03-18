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
