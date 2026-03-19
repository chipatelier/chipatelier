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
# Exclude visually ambiguous characters (0/O and 1/I) for easier transcription
_TOKEN_ALPHABET = "".join(
    c for c in string.ascii_uppercase + string.digits if c not in "0O1I"
)


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
