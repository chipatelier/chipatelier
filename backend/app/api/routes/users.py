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
    resp = UserResponse.model_validate(current_user)
    resp.storage_quota_bytes = None
    return resp
